#!/usr/bin/env python3
"""Assemble local still scenes and authorized audio. Requires FFmpeg + FFprobe."""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import wave
from pathlib import Path

RATE = 48000      # output audio sample rate
CHANNELS = 2      # output audio channels
SAMPLE_BYTES = 2  # 16-bit PCM while assembling


def run(command, timeout=900, cwd=None):
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=timeout, check=False, cwd=cwd)
    if result.returncode:
        raise ValueError(f"{Path(command[0]).name} failed: {result.stderr[-2000:]}")
    return result.stdout


def probe(path, executable="ffprobe", cwd=None):
    return json.loads(run([executable, "-v", "error", "-show_format", "-show_streams",
                           "-of", "json", str(path)], timeout=60, cwd=cwd))


def local_asset(root, value):
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ValueError("asset paths must be nonempty project-relative paths")
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"asset {value} resolves outside the folder containing render.json")
    if not path.is_file():
        raise ValueError(f"asset not found: {value}")
    return path


def validate_config(data, root):
    version = data.get("schema_version") if isinstance(data, dict) else None
    if isinstance(version, bool) or version != 1:
        raise ValueError("render configuration requires schema_version 1")
    video = data.get("video", {})
    if not isinstance(video, dict):
        raise ValueError("video must be an object")
    values = [video.get("width", 1280), video.get("height", 720), video.get("fps", 30)]
    if any(type(value) is not int for value in values):
        raise ValueError("width, height, and fps must be integers")
    width, height, fps = values
    if not (16 <= width <= 7680 and 16 <= height <= 4320 and 1 <= fps <= 120):
        raise ValueError("width must be 16-7680, height 16-4320, and fps 1-120")
    if width % 2 or height % 2:
        raise ValueError("width and height must be even for yuv420p")
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("scenes must be a nonempty list")
    result, identifiers = [], set()
    for scene in scenes:
        if not isinstance(scene, dict):
            raise ValueError("each scene must be an object")
        identifier = scene.get("id")
        if not isinstance(identifier, str) or not identifier.strip() or identifier in identifiers:
            raise ValueError("scene IDs must be nonempty and unique")
        identifiers.add(identifier)
        slide, audio = local_asset(root, scene.get("slide")), local_asset(root, scene.get("audio"))
        hold = scene.get("hold_after", 0)
        if isinstance(hold, bool) or not isinstance(hold, (int, float)) or not math.isfinite(hold) or not 0 <= hold <= 60:
            raise ValueError("hold_after must be a finite number between 0 and 60 seconds")
        result.append((identifier, slide, audio, hold))
    return width, height, fps, result


def work_copy(source, work, stem):
    """Copy an input into the work directory under a short, pattern-free name.

    FFmpeg reads names such as ``slide%03d.png`` as image sequences, so inputs
    are never passed to it under their original names or directories.
    """
    suffix = source.suffix.lower() if source.suffix[1:].isalnum() else ""
    target = work / f"{stem}{suffix}"
    shutil.copyfile(source, target)
    return target.name


def frames_for(seconds, fps):
    # Rounding first keeps float noise such as 30.000000000004 from adding a frame.
    return max(1, math.ceil(round(seconds * fps, 6)))


def sample_at(frame, fps):
    return round(frame * RATE / fps)


def decoded_audio_seconds(ffmpeg, name, work, timeout=900):
    """Decode the first audio stream and count samples without keeping them in memory."""
    log = work / "decode-audio.log"
    with log.open("w", encoding="utf-8") as errors:
        process = subprocess.Popen([ffmpeg, "-nostdin", "-v", "error", "-xerror", "-i", name,
                                    "-map", "0:a:0", "-ac", "1", "-ar", str(RATE), "-f", "s16le", "-"],
                                   cwd=work, stdout=subprocess.PIPE, stderr=errors)
        watchdog = threading.Timer(timeout, process.kill)  # a stalled decoder must not hang the build
        watchdog.start()
        try:
            total = 0
            for chunk in iter(lambda: process.stdout.read(1 << 20), b""):
                total += len(chunk)
            code = process.wait()
        finally:
            watchdog.cancel()
            process.stdout.close()
            if process.poll() is None:
                process.kill()
                process.wait()
    if code:
        raise ValueError(f"audio decode failed or timed out: "
                         f"{log.read_text(encoding='utf-8', errors='replace')[-2000:]}")
    return total / SAMPLE_BYTES / RATE


def add_scene(index, slide, audio, hold, frame_cursor, track, work, quiet, ffprobe, width, height, fps):
    """Render one scene's video-only clip and append its padded narration; return (frames, seconds)."""
    # 1. One still per scene: transparent areas flattened onto white, letterbox bars black,
    #    first frame of animated images. Relative names keep '%' away from FFmpeg.
    source = work_copy(slide, work, f"slide-{index:04}")
    still = f"still-{index:04}.png"
    run(quiet + ["-i", source, "-filter_complex",
                 f"color=c=white:s={width}x{height}[bg];"
                 f"[0:v]format=rgba,scale={width}:{height}:force_original_aspect_ratio=decrease,"
                 f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black[fg];"
                 "[bg][fg]overlay=format=auto,setsar=1,format=rgb24",
                 "-frames:v", "1", "-update", "1", still], cwd=work)
    (work / source).unlink()
    # 2. Decode narration to PCM; its sample count is the duration (container
    #    estimates are wrong for some VBR files).
    spoken = work_copy(audio, work, f"audio-{index:04}")
    metadata = probe(spoken, ffprobe, cwd=work)
    if not any(stream.get("codec_type") == "audio" for stream in metadata.get("streams", [])):
        raise ValueError("no audio stream")
    pcm = f"narr-{index:04}.wav"
    run(quiet + ["-i", spoken, "-vn", "-map", "0:a:0", "-ac", str(CHANNELS),
                 "-ar", str(RATE), "-c:a", "pcm_s16le", pcm], cwd=work)
    (work / spoken).unlink()
    with wave.open(str(work / pcm), "rb") as decoded:
        samples = decoded.getnframes()
        if samples <= 0:
            raise ValueError("audio decodes to no samples")
        # 3. Put the scene on the frame grid; pad (never trim) its audio to that length.
        frames = frames_for(samples / RATE + hold, fps)
        while sample_at(frame_cursor + frames, fps) - sample_at(frame_cursor, fps) < samples:
            frames += 1
        length = sample_at(frame_cursor + frames, fps) - sample_at(frame_cursor, fps)
        for chunk in iter(lambda: decoded.readframes(1 << 16), b""):
            track.writeframes(chunk)
    (work / pcm).unlink()
    track.writeframes(b"\0" * ((length - samples) * CHANNELS * SAMPLE_BYTES))
    # 4. Video-only clip with an exact frame count.
    run(quiet + ["-loop", "1", "-framerate", str(fps), "-i", still,
                 "-frames:v", str(frames), "-an", "-map_metadata", "-1",
                 "-c:v", "libx264", "-preset", "medium", "-tune", "stillimage", "-crf", "20",
                 "-pix_fmt", "yuv420p", "-r", str(fps), f"clip-{index:04}.mp4"], cwd=work)
    (work / still).unlink()
    return frames, samples / RATE


def assemble(config, output, ffmpeg="ffmpeg", ffprobe="ffprobe"):
    config, output = Path(config).resolve(), Path(output).resolve()
    receipt = output.with_suffix(".timeline.json")
    if output.exists() or receipt.exists():
        raise ValueError("output or timeline receipt exists; choose a new output path")
    if output.suffix.lower() != ".mp4":
        raise ValueError("output must have .mp4 extension")
    if not output.parent.is_dir():
        raise ValueError("output parent directory must exist")
    resolved = []
    for executable in (ffmpeg, ffprobe):
        found = shutil.which(executable)
        if not found:
            raise ValueError(f"required executable not found: {executable} "
                             "(add it to the PATH environment variable or pass --ffmpeg/--ffprobe "
                             "with the executable's path)")
        # Absolute, because FFmpeg later runs inside the temporary folder.
        resolved.append(os.path.abspath(found))
    ffmpeg, ffprobe = resolved
    data = json.loads(config.read_text(encoding="utf-8-sig"))
    width, height, fps, scenes = validate_config(data, config.parent)
    quiet = [ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-n"]
    timeline, frame_cursor = [], 0
    # A temporary directory beside the output keeps paths short and publication atomic.
    with tempfile.TemporaryDirectory(prefix="tutorial-render-", dir=output.parent) as temp:
        work = Path(temp)
        narration = work / "narration.wav"
        with wave.open(str(narration), "wb") as track:
            track.setnchannels(CHANNELS)
            track.setsampwidth(SAMPLE_BYTES)
            track.setframerate(RATE)
            for index, (identifier, slide, audio, hold) in enumerate(scenes):
                try:
                    frames, duration = add_scene(index, slide, audio, hold, frame_cursor, track, work,
                                                 quiet, ffprobe, width, height, fps)
                except (ValueError, OSError, wave.Error, subprocess.TimeoutExpired) as exc:
                    where = (f"scene {identifier} (slide {slide.relative_to(config.parent).as_posix()}, "
                             f"audio {audio.relative_to(config.parent).as_posix()})")
                    raise ValueError(f"{where}: {exc}") from exc
                timeline.append({"id": identifier, "start": round(frame_cursor / fps, 6),
                                 "clip_duration": round(frames / fps, 6), "frames": frames,
                                 "audio_duration": round(duration, 6), "requested_hold_after": hold})
                frame_cursor += frames
        total_frames = frame_cursor
        concat = work / "clips.txt"
        concat.write_text("".join(f"file 'clip-{i:04}.mp4'\n" for i in range(len(scenes))), encoding="utf-8")
        run(quiet + ["-f", "concat", "-safe", "1", "-i", concat.name, "-map_metadata", "-1",
                     "-c", "copy", "video.mp4"], cwd=work)
        # Narration is encoded once across the whole timeline, so scene joins add no delay.
        run(quiet + ["-i", "video.mp4", "-i", narration.name, "-map", "0:v:0", "-map", "1:a:0",
                     "-map_metadata", "-1", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                     "-ar", str(RATE), "-ac", str(CHANNELS), "-movflags", "+faststart",
                     "assembled.mp4"], cwd=work)
        run([ffmpeg, "-nostdin", "-v", "error", "-xerror", "-i", "assembled.mp4", "-f", "null", "-"], cwd=work)
        final = probe("assembled.mp4", ffprobe, cwd=work)
        video_streams = [s for s in final.get("streams", []) if s.get("codec_type") == "video"]
        counted = int(video_streams[0].get("nb_frames", 0) or 0) if video_streams else 0
        if video_streams and not counted:  # container without a frame count: decode and count
            counted = int(json.loads(run([ffprobe, "-v", "error", "-count_frames", "-select_streams", "v:0",
                                          "-show_entries", "stream=nb_read_frames", "-of", "json",
                                          "assembled.mp4"], cwd=work))["streams"][0]["nb_read_frames"])
        if counted != total_frames:
            raise ValueError(f"video has {counted} frames; the timeline expects {total_frames}")
        video_seconds = total_frames / fps
        audio_seconds = decoded_audio_seconds(ffmpeg, "assembled.mp4", work)
        if abs(audio_seconds - video_seconds) > 1 / fps + 1024 / RATE:
            raise ValueError(f"decoded audio lasts {audio_seconds:.3f} s but video lasts "
                             f"{video_seconds:.3f} s; inspect the timeline")
        built = work / "assembled.mp4"
        # Exclusive creation prevents replacing files created by another process meanwhile.
        with output.open("xb") as stream, built.open("rb") as source:
            shutil.copyfileobj(source, stream)
        payload = {"schema_version": 1, "duration": float(final["format"]["duration"]),
                   "video_duration": round(video_seconds, 6),
                   "decoded_audio_duration": round(audio_seconds, 6), "fps": fps,
                   "scenes": timeline,
                   "timeline_basis": "frame-grid scene offsets; one continuous audio track encoded once",
                   "ffmpeg": run([ffmpeg, "-version"], timeout=15).splitlines()[0],
                   "technical_decode": "pass", "listening_and_visual_review": "not performed"}
        with receipt.open("x", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2)
            stream.write("\n")
    return payload


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config")
    parser.add_argument("--out", required=True)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    args = parser.parse_args()
    try:
        result = assemble(args.config, args.out, args.ffmpeg, args.ffprobe)
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, subprocess.TimeoutExpired, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
