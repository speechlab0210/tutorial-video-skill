import copy
import hashlib
import importlib.util
import json
import math
import os
import shutil
import struct
import subprocess
import tempfile
import unittest
import wave
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

    def test_project_relative_asset_boundary(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inside = root / "project"
            inside.mkdir()
            (root / "outside.wav").write_bytes(b"outside")
            with self.assertRaises(ValueError):
                assembler.local_asset(inside, "../outside.wav")
            with self.assertRaises(ValueError):
                assembler.local_asset(inside, str(root / "outside.wav"))

    def test_invalid_render_dimensions_and_hold(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "image.ppm").write_bytes(b"image")
            (root / "tone.wav").write_bytes(b"audio")
            data = {"schema_version": 1, "video": {"width": 321}, "scenes": [
                {"id": "S1", "slide": "image.ppm", "audio": "tone.wav", "hold_after": 0}]}
            with self.assertRaises(ValueError):
                assembler.validate_config(data, root)
            data["video"]["width"] = 320
            for value in (-1, float("nan"), True, 61):
                data["scenes"][0]["hold_after"] = value
                with self.assertRaises(ValueError):
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


if __name__ == "__main__":
    unittest.main()
