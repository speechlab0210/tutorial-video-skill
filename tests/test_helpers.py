import copy
import hashlib
import importlib.util
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import wave
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "tutorial-video"


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, SKILL / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


project = load_module("tutorial_project", "project.py")
assembler = load_module("tutorial_assembler", "assemble.py")
FFMPEG = os.environ.get("FFMPEG_BINARY", "ffmpeg")
FFPROBE = os.environ.get("FFPROBE_BINARY", "ffprobe")


def write_wav(path, samples, rate=48000):
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(rate)
        stream.writeframes(struct.pack("<" + "h" * len(samples), *samples))


def tone(seconds, frequency=440, amplitude=10000, rate=48000):
    return [int(amplitude * math.sin(2 * math.pi * frequency * i / rate)) for i in range(int(seconds * rate))]


def write_ppm(path, color, width=32, height=18):
    Path(path).write_bytes(f"P6\n{width} {height}\n255\n".encode() + bytes(color) * (width * height))


def write_rgba_png(path, pixel, width, height):
    rows = b"".join(b"\0" + b"".join(bytes(pixel(x, y)) for x in range(width)) for y in range(height))
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
                           + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def run_helper(*args, **env):
    """Run project.py; env values override os.environ and None removes a variable."""
    merged = {**os.environ, **env}
    return subprocess.run([sys.executable, str(SKILL / "scripts" / "project.py"), *map(str, args)],
                          capture_output=True, timeout=60,
                          env={key: value for key, value in merged.items() if value is not None})


def decode_pcm(path, rate=48000):
    pcm = subprocess.check_output([FFMPEG, "-v", "error", "-i", str(path), "-vn", "-ac", "1",
                                   "-ar", str(rate), "-f", "s16le", "-"], timeout=120)
    return struct.unpack("<" + "h" * (len(pcm) // 2), pcm)


def frame_pixels(path, moment, width=1):
    return subprocess.check_output([FFMPEG, "-v", "error", "-ss", str(moment), "-i", str(path), "-frames:v", "1",
                                    "-vf", f"scale={width}:1", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"], timeout=60)


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.plan = project.read_json(SKILL / "assets/examples/weighted-averages.json")

    def test_complete_worked_example(self):
        self.assertEqual(project.check_project(self.plan), ([], []))

    def test_duplicate_scene_identity(self):
        self.plan["scenes"].append(copy.deepcopy(self.plan["scenes"][0]))
        errors, _ = project.check_project(self.plan)
        self.assertTrue(any("duplicate scenes" in error for error in errors))

    def test_missing_objective_and_broken_reference(self):
        self.plan["objectives"].append({"id": "UNUSED", "text": "Uncovered outcome"})
        self.plan["scenes"][0]["objective_ids"] = ["UNKNOWN"]
        errors, _ = project.check_project(self.plan)
        self.assertTrue(any("UNUSED has no scene" in error for error in errors))
        self.assertTrue(any("unknown objective_ids" in error for error in errors))

    def test_source_claim_requires_conditions_and_location(self):
        self.plan["claims"][0]["kind"] = "source"
        self.plan["claims"][0].pop("conditions")
        errors, _ = project.check_project(self.plan)
        self.assertTrue(any("source is required" in error for error in errors))
        self.assertTrue(any("conditions is required" in error for error in errors))
        self.assertTrue(any("location is required" in error for error in errors))

    def test_malformed_nested_values_do_not_crash(self):
        for section in ([], {}, None):
            with self.subTest(section=section):
                plan = copy.deepcopy(self.plan)
                plan["scenes"][0]["section"] = section
                self.assertTrue(project.check_project(plan)[0])
        self.assertTrue(project.check_project([])[0])
        self.plan["scenes"][0]["beats"] = None
        self.assertTrue(project.check_project(self.plan)[0])

    def test_unverified_claim_is_warning_not_factual_pass(self):
        self.plan["claims"][0]["status"] = "unverified"
        errors, warnings = project.check_project(self.plan)
        self.assertFalse(errors)
        self.assertTrue(warnings)

    def test_duplicate_beat_id(self):
        self.plan["scenes"][1]["beats"][0]["id"] = "B1"
        self.assertTrue(any("duplicate beat" in item for item in project.check_project(self.plan)[0]))

    def test_boolean_schema_version_and_kind_message(self):
        self.plan["schema_version"] = True
        self.plan["claims"][0]["kind"] = "contested"
        errors, _ = project.check_project(self.plan)
        self.assertIn("schema_version must be 1", errors)
        self.assertTrue(any("'contested'" in item and "expected source" in item for item in errors))

    def test_reports_survive_a_non_utf8_console(self):
        plan = copy.deepcopy(self.plan)
        plan["title"] = "加權平均 ≈ ¿ 简体 🙂"
        plan["scenes"][0]["narration"] = "這是第一個場景 ≈ 🙂"
        default = {"PYTHONIOENCODING": None, "PYTHONUTF8": None}  # a piped Windows run uses the locale code page
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "project.json"
            project.write_json(path, plan)
            result = run_helper("outline", path, **default)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("這是第一個場景 ≈ 🙂", result.stdout.decode("utf-8"))
            # An explicit legacy encoding is respected; unencodable text is escaped instead of crashing.
            result = run_helper("outline", path, PYTHONIOENCODING="cp1252", PYTHONUTF8=None)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("\\u9019", result.stdout.decode("cp1252"))
            plan["scenes"][0]["id"] = "場景一"
            plan["scenes"][0]["section"] = "章節不存在"
            broken = Path(temp) / "broken.json"
            project.write_json(broken, plan)
            result = run_helper("check", broken, **default)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("scene 場景一: unknown section", result.stdout.decode("utf-8"))
            result = run_helper("check", temp)
            self.assertEqual(result.returncode, 2)
            self.assertIn(b"pass the path to its project.json", result.stderr)

    def test_init_is_incomplete_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "new lesson"
            project.init_project(folder)
            self.assertTrue(project.check_project(project.read_json(folder / "project.json"))[0])
            initial = (folder / "brief.md").read_bytes()
            with self.assertRaises(ValueError):
                project.init_project(folder)
            self.assertEqual((folder / "brief.md").read_bytes(), initial)


class CaptionTests(unittest.TestCase):
    def test_unicode_bom_crlf(self):
        text = "\ufeff1\r\n00:00:00,100 --> 00:00:01,000\r\n這是範例。\r\n\r\n2\r\n00:00:01,050 --> 00:00:02,000\r\nA second cue.\r\n"
        self.assertEqual(project.check_captions(text, 2), ([], [], 2))

    def test_overlap_and_overrun(self):
        text = "1\n00:00:00,000 --> 00:00:02,000\nOne\n\n2\n00:00:01,000 --> 00:00:04,000\nTwo"
        errors, _, _ = project.check_captions(text, 3)
        self.assertTrue(any("overlaps" in item for item in errors))
        self.assertTrue(any("past measured" in item for item in errors))

    def test_invalid_intervals_and_duration(self):
        text = "1\n00:00:03,000 --> 00:00:02,000\nReversed"
        self.assertTrue(project.check_captions(text, 5)[0])
        self.assertTrue(project.check_captions(text, float("nan"))[0])
        self.assertTrue(project.check_captions("")[0])

    def test_extra_blank_lines_between_cues(self):
        one, two = "1\n00:00:00,000 --> 00:00:01,000\nOne", "2\n00:00:01,000 --> 00:00:02,000\nTwo"
        for gap in ("\n\n\n", "\n \t\n\n", "\n\n\n\n"):
            for text in (one + gap + two, (one + gap + two).replace("\n", "\r\n")):
                with self.subTest(gap=gap, crlf="\r" in text):
                    self.assertEqual(project.check_captions(text, 2), ([], [], 2))

    def test_report_says_when_duration_was_not_checked(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "captions.srt"
            path.write_text("1\n00:00:00,000 --> 00:00:09,000\n字幕\n", encoding="utf-8")
            report = json.loads(run_helper("captions", path).stdout.decode("utf-8"))
            self.assertEqual(report["duration_check"], "not performed (pass --duration)")
            result = run_helper("captions", path, "--duration", "5")
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout.decode("utf-8"))["duration_check"], "performed")
            for invalid in ("-1", "0", "nan", "inf"):
                result = run_helper("captions", path, "--duration", invalid)
                self.assertEqual(result.returncode, 2, invalid)
                self.assertEqual(result.stdout, b"")


class IntegrityTests(unittest.TestCase):
    def test_hashes_track_actual_bytes_and_relative_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            path = folder / "transcript.txt"
            path.write_bytes(b"first")
            initial = project.make_manifest(folder)
            self.assertEqual(initial["files"][0]["path"], "transcript.txt")
            self.assertEqual(initial["files"][0]["sha256"], hashlib.sha256(b"first").hexdigest())
            path.write_bytes(b"changed")
            self.assertNotEqual(project.make_manifest(folder), initial)

    def test_exclusive_json_write(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "manifest.json"
            project.write_json(path, {"value": 1})
            with self.assertRaises(FileExistsError):
                project.write_json(path, {"value": 2})
            self.assertEqual(project.read_json(path), {"value": 1})

    def test_empty_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                project.make_manifest(temp)

    def test_manifest_order_does_not_depend_on_platform(self):
        with tempfile.TemporaryDirectory() as temp:
            for name in ("a.txt", "B.txt", "sub/c.txt"):
                (Path(temp) / name).parent.mkdir(exist_ok=True)
                (Path(temp) / name).write_bytes(name.encode())
            paths = [entry["path"] for entry in project.make_manifest(temp)["files"]]
            self.assertEqual(paths, ["B.txt", "a.txt", "sub/c.txt"])

    def test_manifest_rejects_links_and_junctions(self):
        def junction(link, target):
            result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True, timeout=30)
            if result.returncode:
                raise OSError(result.stderr)

        def symlink(link, target):
            link.symlink_to(target, target_is_directory=True)

        kinds = [("symlink", symlink)] + ([("junction", junction)] if os.name == "nt" else [])
        for kind, make in kinds:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                root, outside = Path(temp) / "deliverables", Path(temp) / "outside"
                root.mkdir()
                outside.mkdir()
                (root / "video.txt").write_bytes(b"inside")
                (outside / "private.txt").write_bytes(b"outside")
                try:
                    make(root / "linked", outside)
                except OSError:
                    self.skipTest(f"cannot create a {kind} here")
                with self.assertRaisesRegex(ValueError, "links are not supported"):
                    project.make_manifest(root)

    def test_project_relative_asset_boundary(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            inside = root / "project"
            inside.mkdir()
            (root / "outside.wav").write_bytes(b"outside")
            (inside / "inside.wav").write_bytes(b"inside")
            self.assertEqual(assembler.local_asset(inside, "inside.wav"), inside / "inside.wav")
            with self.assertRaisesRegex(ValueError, "outside the folder containing render.json"):
                assembler.local_asset(inside, "../outside.wav")
            with self.assertRaisesRegex(ValueError, "asset not found"):
                assembler.local_asset(inside, "missing.wav")
            with self.assertRaises(ValueError):
                assembler.local_asset(inside, str(root / "outside.wav"))

    def test_relative_executable_is_made_absolute(self):
        """FFmpeg runs inside the temporary folder, so a relative --ffmpeg path must not stay relative."""
        name = "fake-ffmpeg.exe" if os.name == "nt" else "fake-ffmpeg"
        calls, original_run, original_cwd = [], assembler.subprocess.run, os.getcwd()
        def record(command, **kwargs):
            calls.append(command[0])
            return subprocess.CompletedProcess(command, 1, "", "stop after the first call")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            (root / "tools").mkdir()
            (root / "tools" / name).write_bytes(b"")
            (root / "tools" / name).chmod(0o755)
            write_ppm(root / "slide.ppm", (0, 0, 0))
            write_wav(root / "tone.wav", tone(0.1))
            project.write_json(root / "render.json", {"schema_version": 1, "scenes": [
                {"id": "S1", "slide": "slide.ppm", "audio": "tone.wav"}]})
            try:
                os.chdir(root)
                assembler.subprocess.run = record
                with self.assertRaises(ValueError):
                    assembler.assemble("render.json", "out.mp4", f"tools/{name}", f"tools/{name}")
            finally:
                assembler.subprocess.run = original_run
                os.chdir(original_cwd)
            self.assertTrue(calls and all(os.path.isabs(path) for path in calls), calls)

    def test_invalid_render_dimensions_and_hold(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            (root / "image.ppm").write_bytes(b"image")
            (root / "tone.wav").write_bytes(b"audio")
            data = {"schema_version": 1, "video": {"width": 321}, "scenes": [
                {"id": "S1", "slide": "image.ppm", "audio": "tone.wav", "hold_after": 0}]}
            with self.assertRaises(ValueError):
                assembler.validate_config(data, root)
            data["video"]["width"] = 320
            self.assertEqual(assembler.validate_config(data, root),
                             (320, 720, 30, [("S1", root / "image.ppm", root / "tone.wav", 0)]))
            for value in (-1, float("nan"), True, 61):
                data["scenes"][0]["hold_after"] = value
                with self.assertRaisesRegex(ValueError, "hold_after"):
                    assembler.validate_config(data, root)
            data["scenes"][0]["hold_after"] = 0
            data["schema_version"] = True
            with self.assertRaisesRegex(ValueError, "schema_version"):
                assembler.validate_config(data, root)


@unittest.skipUnless(shutil.which(FFMPEG) and shutil.which(FFPROBE), "FFmpeg/FFprobe unavailable: integration NOT verified")
class MediaIntegrationTests(unittest.TestCase):
    def test_actual_movie_scene_order_audio_hold_and_no_overwrite(self):
        with tempfile.TemporaryDirectory(prefix="tutorial media test ") as temp:
            root = Path(temp)
            for name, color, frequency in (("red", (255, 0, 0), 440), ("blue", (0, 0, 255), 660)):
                (root / f"{name}.ppm").write_bytes(b"P6\n32 18\n255\n" + bytes(color) * (32 * 18))
                samples = [int(10000 * math.sin(2 * math.pi * frequency * i / 48000)) for i in range(48000)]
                with wave.open(str(root / f"{name}.wav"), "wb") as stream:
                    stream.setnchannels(1)
                    stream.setsampwidth(2)
                    stream.setframerate(48000)
                    stream.writeframes(struct.pack("<" + "h" * len(samples), *samples))
            config = {"schema_version": 1, "video": {"width": 320, "height": 180, "fps": 25},
                      "scenes": [{"id": name, "slide": f"{name}.ppm", "audio": f"{name}.wav", "hold_after": 0.4}
                                 for name in ("red", "blue")]}
            project.write_json(root / "render.json", config)
            output = root / "course.mp4"
            result = assembler.assemble(root / "render.json", output, FFMPEG, FFPROBE)
            self.assertAlmostEqual(result["duration"], 2.8, delta=0.12)
            self.assertEqual([row["id"] for row in result["scenes"]], ["red", "blue"])
            self.assertTrue(output.with_suffix(".timeline.json").exists())
            for moment, channel in ((0.2, 0), (1.8, 2)):
                data = subprocess.check_output([FFMPEG, "-v", "error", "-ss", str(moment), "-i", str(output),
                                                "-frames:v", "1", "-vf", "scale=1:1", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"], timeout=60)
                self.assertGreater(data[channel], 200)
                self.assertLess(data[(channel + 1) % 3], 30)
            pcm = subprocess.check_output([FFMPEG, "-v", "error", "-i", str(output), "-vn", "-ac", "1",
                                           "-ar", "48000", "-f", "s16le", "-"], timeout=60)
            values = struct.unpack("<" + "h" * (len(pcm) // 2), pcm)
            def rms(start, end):
                sample = values[int(start * 48000):int(end * 48000)]
                return math.sqrt(sum(value * value for value in sample) / len(sample))
            self.assertGreater(rms(0.2, 0.7), 1000)
            self.assertGreater(rms(1.7, 2.1), 1000)
            self.assertLess(rms(2.62, 2.72), 30)
            before = hashlib.sha256(output.read_bytes()).hexdigest()
            with self.assertRaises(ValueError):
                assembler.assemble(root / "render.json", output, FFMPEG, FFPROBE)
            self.assertEqual(hashlib.sha256(output.read_bytes()).hexdigest(), before)

    def test_narration_stays_on_its_slide_across_many_joins(self):
        """Slide changes and speech onsets are measured in the shipped MP4, not in the plan."""
        for fps in (30, 7):  # 48000/7 is not an integer, which exercises the sample rounding
            with self.subTest(fps=fps):
                self.check_sync(fps)

    def check_sync(self, fps):
        rate = 48000
        lengths = [0.41, 0.53, 0.67, 0.44, 0.79, 0.58, 0.89, 0.47, 0.61, 0.73, 0.52, 0.85]
        holds = [0, 0.07, 0, 0.13, 0, 0.05, 0, 0, 0.11, 0, 0.02, 0.3]
        with tempfile.TemporaryDirectory(prefix="tutorial sync test ") as temp:
            root = Path(temp)
            write_ppm(root / "black.ppm", (0, 0, 0), 64, 36)
            write_ppm(root / "white.ppm", (255, 255, 255), 64, 36)
            scenes = []
            for index, (length, hold) in enumerate(zip(lengths, holds)):
                burst = tone(0.03, 1000, 12000)
                write_wav(root / f"s{index}.wav", burst + [0] * (int(length * rate) - len(burst)))
                scenes.append({"id": f"S{index}", "slide": ("black.ppm", "white.ppm")[index % 2],
                               "audio": f"s{index}.wav", "hold_after": hold})
            project.write_json(root / "render.json", {"schema_version": 1, "scenes": scenes,
                                                      "video": {"width": 64, "height": 36, "fps": fps}})
            output = root / "sync.mp4"
            result = assembler.assemble(root / "render.json", output, FFMPEG, FFPROBE)
            luma = subprocess.check_output([FFMPEG, "-v", "error", "-i", str(output), "-vf", "scale=1:1,format=gray",
                                            "-f", "rawvideo", "-"], timeout=120)
            changes = [i / fps for i in range(1, len(luma)) if (luma[i] > 128) != (luma[i - 1] > 128)]
            samples = decode_pcm(output)
            onsets, quiet_until = [], 0
            for i, value in enumerate(samples):
                if abs(value) > 3000:
                    if i >= quiet_until:
                        onsets.append(i / rate)
                    quiet_until = i + int(0.2 * rate)
            self.assertEqual(len(changes), len(lengths) - 1)
            self.assertEqual(len(onsets), len(lengths))
            for index, (change, onset) in enumerate(zip(changes, onsets[1:]), 1):
                with self.subTest(scene=index):
                    self.assertLessEqual(abs(onset - change), 0.01)
                    self.assertLessEqual(abs(result["scenes"][index]["start"] - change), 0.001)
            self.assertLessEqual(abs(len(samples) / rate - len(luma) / fps), 1 / fps + 1024 / rate)

    def test_scene_errors_name_the_scene_and_file(self):
        with tempfile.TemporaryDirectory(prefix="tutorial error test ") as temp:
            root = Path(temp)
            write_ppm(root / "slide.ppm", (0, 0, 0))
            write_wav(root / "intro.wav", tone(0.3))
            (root / "broken.wav").write_bytes(b"not audio at all")
            project.write_json(root / "render.json", {"schema_version": 1, "scenes": [
                {"id": "intro", "slide": "slide.ppm", "audio": "intro.wav"},
                {"id": "chart", "slide": "slide.ppm", "audio": "broken.wav"}]})
            with self.assertRaisesRegex(ValueError, r"scene chart \(slide slide\.ppm, audio broken\.wav\)"):
                assembler.assemble(root / "render.json", root / "out.mp4", FFMPEG, FFPROBE)
            self.assertEqual(sorted(path.name for path in root.iterdir()),
                             ["broken.wav", "intro.wav", "render.json", "slide.ppm"])

    def test_vbr_mp3_keeps_its_ending_and_hold(self):
        encoders = subprocess.run([FFMPEG, "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=30).stdout
        if "libmp3lame" not in encoders:
            self.skipTest("libmp3lame unavailable")
        with tempfile.TemporaryDirectory(prefix="tutorial vbr test ") as temp:
            root = Path(temp)
            write_ppm(root / "slide.ppm", (255, 0, 0))
            noise = [int(9000 * math.sin(i * i * 0.001)) for i in range(int(0.3 * 48000))]
            write_wav(root / "speech.wav", noise + tone(1.2, 440, 9000))
            subprocess.run([FFMPEG, "-v", "error", "-i", str(root / "speech.wav"), "-c:a", "libmp3lame",
                            "-q:a", "6", "-write_xing", "0", str(root / "speech.mp3")], check=True, timeout=60)
            project.write_json(root / "render.json", {"schema_version": 1, "video": {"width": 64, "height": 36, "fps": 25},
                                                      "scenes": [{"id": "S1", "slide": "slide.ppm",
                                                                  "audio": "speech.mp3", "hold_after": 0.5}]})
            output = root / "vbr.mp4"
            result = assembler.assemble(root / "render.json", output, FFMPEG, FFPROBE)
            self.assertGreater(result["scenes"][0]["audio_duration"], 1.45)
            samples = decode_pcm(output)
            def rms(start, end):
                part = samples[int(start * 48000):int(end * 48000)]
                return math.sqrt(sum(value * value for value in part) / len(part))
            self.assertGreater(rms(1.35, 1.45), 1000)
            self.assertLess(rms(1.6, 1.9), 30)

    def test_awkward_slide_files(self):
        with tempfile.TemporaryDirectory(prefix="tutorial % slides ") as temp:
            root = Path(temp)
            for name, color in (("red", (255, 0, 0)), ("blue", (0, 0, 255)), ("green", (0, 200, 0)),
                                ("yellow", (255, 255, 0))):
                write_ppm(root / f"{name}.ppm", color)
            convert = [FFMPEG, "-v", "error", "-i"]
            subprocess.run(convert + [str(root / "red.ppm"), str(root / "red.png")], check=True, timeout=60)
            subprocess.run(convert + [str(root / "blue.ppm"), str(root / "slide001.png")], check=True, timeout=60)
            os.replace(root / "red.png", root / "slide%03d.png")  # FFmpeg itself would expand the pattern
            subprocess.run(convert + [str(root / "green.ppm"), str(root / "green.gif")], check=True, timeout=60)
            subprocess.run(convert + [str(root / "yellow.ppm"), "-f", "mjpeg", str(root / "yellow.png")],
                           check=True, timeout=60)
            write_rgba_png(root / "transparent.png", lambda x, y: (0, 0, 0, 255) if x < 16 else (0, 0, 0, 0), 32, 18)
            write_wav(root / "tone.wav", tone(0.5))
            slides = ["slide%03d.png", "transparent.png", "green.gif", "yellow.png"]
            project.write_json(root / "render.json", {"schema_version": 1, "video": {"width": 64, "height": 36, "fps": 10},
                                                      "scenes": [{"id": f"S{i}", "slide": name, "audio": "tone.wav"}
                                                                 for i, name in enumerate(slides)]})
            result = assembler.assemble(root / "render.json", root / "slides.mp4", FFMPEG, FFPROBE)
            middle = [row["start"] + 0.25 for row in result["scenes"]]
            red = frame_pixels(root / "slides.mp4", middle[0])
            self.assertTrue(red[0] > 200 and red[2] < 60, red)
            left_right = frame_pixels(root / "slides.mp4", middle[1], 2)
            self.assertLess(max(left_right[:3]), 60)
            self.assertGreater(min(left_right[3:]), 200)
            green = frame_pixels(root / "slides.mp4", middle[2])
            self.assertTrue(green[1] > 150 and green[0] < 80, green)
            yellow = frame_pixels(root / "slides.mp4", middle[3])
            self.assertTrue(yellow[0] > 200 and yellow[1] > 200 and yellow[2] < 80, yellow)


if __name__ == "__main__":
    unittest.main()
