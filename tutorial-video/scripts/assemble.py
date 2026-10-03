#!/usr/bin/env python3
"""Assemble local still scenes and authorized audio. Requires FFmpeg + FFprobe."""
import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run(command, timeout=900):
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=timeout, check=False)
    if result.returncode:
        raise ValueError(f"{Path(command[0]).name} failed: {result.stderr[-2000:]}")
    return result.stdout


def probe(path, executable="ffprobe"):
    return json.loads(run([executable, "-v", "error", "-show_format", "-show_streams",
                           "-of", "json", str(path)], timeout=60))


def local_asset(root, value):
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ValueError("asset paths must be nonempty project-relative paths")
    path = (root / value).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f"asset missing or outside project: {value}")
    return path


def validate_config(data, root):
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("render configuration requires schema_version 1")
    video = data.get("video", {})
    if not isinstance(video, dict):
        raise ValueError("video must be an object")
    values = [video.get("width", 1280), video.get("height", 720), video.get("fps", 30)]
    if any(type(value) is not int for value in values):
        raise ValueError("width, height, and fps must be integers")
    width, height, fps = values
    if not (16 <= width <= 7680 and 16 <= height <= 4320 and 1 <= fps <= 120):
        raise ValueError("unsupported dimensions or fps")
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


def assemble(config, output, ffmpeg="ffmpeg", ffprobe="ffprobe"):
    config, output = Path(config).resolve(), Path(output).resolve()
    receipt = output.with_suffix(".timeline.json")
    if output.exists() or receipt.exists():
        raise ValueError("output or timeline receipt exists; choose a new output path")
    if output.suffix.lower() != ".mp4":
        raise ValueError("output must have .mp4 extension")
    if not output.parent.is_dir():
        raise ValueError("output parent directory must exist")
    for executable in (ffmpeg, ffprobe):
        if not shutil.which(executable):
            raise ValueError(f"required executable not found: {executable}")
    data = json.loads(config.read_text(encoding="utf-8-sig"))
    width, height, fps, scenes = validate_config(data, config.parent)
    timeline, offset = [], 0.0
    # A temporary directory beside the output keeps paths short and publication atomic.
    with tempfile.TemporaryDirectory(prefix="tutorial-render-", dir=output.parent) as temp:
        work = Path(temp)
        for index, (identifier, slide, audio, hold) in enumerate(scenes):
            metadata = probe(audio, ffprobe)
            if not any(stream.get("codec_type") == "audio" for stream in metadata.get("streams", [])):
                raise ValueError(f"scene {identifier}: no audio stream")
            duration = float(metadata.get("format", {}).get("duration", "nan"))
            if not math.isfinite(duration) or duration <= 0:
                raise ValueError(f"scene {identifier}: invalid audio duration")
            requested = math.ceil((duration + hold) * fps) / fps
            clip = work / f"clip-{index:04}.mp4"
            run([ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-n",
                 "-loop", "1", "-framerate", str(fps), "-i", str(slide), "-i", str(audio),
                 "-map", "0:v:0", "-map", "1:a:0", "-map_metadata", "-1",
                 "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1",
                 "-af", "apad", "-t", f"{requested:.9f}", "-r", str(fps),
                 "-c:v", "libx264", "-preset", "medium", "-tune", "stillimage", "-crf", "20",
                 "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                 "-ac", "2", "-movflags", "+faststart", str(clip)])
            actual = float(probe(clip, ffprobe)["format"]["duration"])
            timeline.append({"id": identifier, "start": round(offset, 6),
                             "clip_duration": actual, "audio_duration": duration,
                             "requested_hold_after": hold})
            offset += actual
        concat = work / "clips.txt"
        concat.write_text("".join(f"file 'clip-{i:04}.mp4'\n" for i in range(len(scenes))), encoding="utf-8")
        built = work / "assembled.mp4"
        run([ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-n", "-f", "concat",
             "-safe", "1", "-i", str(concat), "-map_metadata", "-1", "-c", "copy",
             "-movflags", "+faststart", str(built)])
        final = probe(built, ffprobe)
        actual_duration = float(final["format"]["duration"])
        if abs(actual_duration - offset) > max(0.25, len(scenes) / fps):
            raise ValueError("unexpected concatenation duration; inspect the timeline")
        run([ffmpeg, "-nostdin", "-v", "error", "-xerror", "-i", str(built), "-f", "null", "-"])
        # Exclusive creation prevents replacing files created by another process meanwhile.
        with output.open("xb") as stream, built.open("rb") as source:
            shutil.copyfileobj(source, stream)
        payload = {"schema_version": 1, "duration": actual_duration, "scenes": timeline,
                   "timeline_basis": "measured clip container durations; inspect joins in final playback",
                   "ffmpeg": run([ffmpeg, "-version"], timeout=15).splitlines()[0],
                   "technical_decode": "pass", "listening_and_visual_review": "not performed"}
        with receipt.open("x", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2)
            stream.write("\n")
    return payload


def main():
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
