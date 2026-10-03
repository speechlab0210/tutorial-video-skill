#!/usr/bin/env python3
"""Offline planning, caption, and integrity helpers. No network or paid services."""
import argparse
import hashlib
import json
import math
import re
import shutil
import sys
from pathlib import Path


def read_json(path):
    with Path(path).open(encoding="utf-8-sig") as stream:
        return json.load(stream)


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def check_project(data):
    errors, warnings = [], []
    if not isinstance(data, dict):
        return ["project must be an object"], []
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    for key in ("title", "audience", "language", "central_question"):
        if not nonempty(data.get(key)):
            errors.append(f"{key} must be nonempty text")

    def index(key, required):
        values = data.get(key)
        if not isinstance(values, list) or (required and not values):
            errors.append(f"{key} must be {'a nonempty' if required else 'a'} list")
            return {}
        result = {}
        for pos, item in enumerate(values):
            where = f"{key}[{pos}]"
            if not isinstance(item, dict):
                errors.append(f"{where} must be an object")
                continue
            identifier = item.get("id")
            if not nonempty(identifier):
                errors.append(f"{where}.id must be nonempty text")
                continue
            if identifier in result:
                errors.append(f"duplicate {key} id: {identifier}")
            result[identifier] = item
        return result

    objectives = index("objectives", True)
    sections = index("sections", True)
    claims = index("claims", False)
    scenes = index("scenes", True)
    for identifier, item in objectives.items():
        if not nonempty(item.get("text")):
            errors.append(f"objective {identifier}: text is required")
    for identifier, item in sections.items():
        if not nonempty(item.get("question")):
            errors.append(f"section {identifier}: question is required")
    for identifier, item in claims.items():
        if not nonempty(item.get("text")):
            errors.append(f"claim {identifier}: text is required")
        if item.get("kind") not in ("source", "demonstration", "illustration", "interpretation"):
            errors.append(f"claim {identifier}: invalid kind")
        if item.get("kind") in ("source", "interpretation"):
            for field in ("source", "location", "conditions"):
                if not nonempty(item.get(field)):
                    errors.append(f"claim {identifier}: {field} is required")
        if item.get("status") != "verified":
            warnings.append(f"claim {identifier}: not verified; inspect before use")

    covered, used_sections, used_claims = set(), set(), set()
    beat_ids = set()
    for identifier, item in scenes.items():
        for key in ("title", "narration", "transition"):
            if not nonempty(item.get(key)):
                errors.append(f"scene {identifier}: {key} is required")
        section = item.get("section")
        if not isinstance(section, str) or section not in sections:
            errors.append(f"scene {identifier}: unknown section")
        else:
            used_sections.add(section)
        for field, mapping, seen, required in (
            ("objective_ids", objectives, covered, True),
            ("claim_ids", claims, used_claims, False),
        ):
            values = item.get(field, [])
            if not isinstance(values, list) or (required and not values):
                errors.append(f"scene {identifier}: {field} must be {'a nonempty' if required else 'a'} list")
                continue
            for value in values:
                if not isinstance(value, str) or value not in mapping:
                    errors.append(f"scene {identifier}: unknown {field} entry {value!r}")
                else:
                    seen.add(value)
        beats = item.get("beats", [])
        if not isinstance(beats, list):
            errors.append(f"scene {identifier}: beats must be a list")
            continue
        if not beats:
            warnings.append(f"scene {identifier}: no beat-to-visual mapping")
        for beat in beats:
            if not isinstance(beat, dict):
                errors.append(f"scene {identifier}: beat must be an object")
                continue
            bid = beat.get("id")
            if not nonempty(bid):
                errors.append(f"scene {identifier}: beat id is required")
            elif bid in beat_ids:
                errors.append(f"duplicate beat id: {bid}")
            else:
                beat_ids.add(bid)
            for key in ("spoken", "visual", "cue"):
                if not nonempty(beat.get(key)):
                    errors.append(f"scene {identifier}: beat {bid}: {key} is required")
    for identifier in objectives.keys() - covered:
        errors.append(f"objective {identifier} has no scene")
    for identifier in sections.keys() - used_sections:
        errors.append(f"section {identifier} has no scene")
    for identifier in claims.keys() - used_claims:
        warnings.append(f"claim {identifier} is unused")
    return sorted(errors), sorted(warnings)


def init_project(target):
    target = Path(target)
    if target.exists():
        raise ValueError("target already exists; choose a new project directory")
    target.mkdir(parents=True)
    templates = Path(__file__).resolve().parent.parent / "assets" / "templates"
    for filename in ("brief.md", "claims.csv", "revision.md", "review.md"):
        shutil.copyfile(templates / filename, target / filename)
    data = {
        "schema_version": 1, "title": "", "audience": "", "language": "",
        "central_question": "", "objectives": [{"id": "O1", "text": ""}],
        "sections": [{"id": "SEC1", "question": ""}], "claims": [],
        "scenes": [{"id": "S1", "section": "SEC1", "objective_ids": ["O1"],
                    "claim_ids": [], "title": "", "narration": "", "transition": "",
                    "beats": []}],
    }
    write_json(target / "project.json", data)
    print("Created an incomplete planning template. Fill it before running check.")


TIME = r"(\d{2,}):([0-5]\d):([0-5]\d),(\d{3})"
TIMING = re.compile(rf"^{TIME}\s+-->\s+{TIME}$")


def seconds(parts):
    hours, minutes, secs, millis = map(int, parts)
    return hours * 3600 + minutes * 60 + secs + millis / 1000


def check_captions(text, duration=None):
    errors, warnings = [], []
    if duration is not None and (not math.isfinite(duration) or duration <= 0):
        return ["duration must be finite and positive"], [], 0
    text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return ["caption file is empty"], [], 0
    blocks = re.split(r"\n[ \t]*\n", text)
    previous_end = 0.0
    for position, block in enumerate(blocks, 1):
        lines = block.splitlines()
        if len(lines) < 3:
            errors.append(f"cue {position}: needs index, timing, and text")
            continue
        if lines[0].strip() != str(position):
            errors.append(f"cue {position}: index must be {position}")
        match = TIMING.fullmatch(lines[1].strip())
        if not match:
            errors.append(f"cue {position}: invalid SRT timing")
            continue
        start, end = seconds(match.groups()[:4]), seconds(match.groups()[4:])
        if end <= start:
            errors.append(f"cue {position}: end must follow start")
        if start < previous_end - 0.001:
            errors.append(f"cue {position}: overlaps or precedes previous cue")
        if duration is not None and end > duration + 0.05:
            errors.append(f"cue {position}: extends past measured video duration")
        if not "".join(lines[2:]).strip():
            errors.append(f"cue {position}: text is empty")
        if len(lines[2:]) > 2:
            warnings.append(f"cue {position}: more than two lines; inspect readability")
        previous_end = max(previous_end, end)
    return errors, warnings, len(blocks)


def make_manifest(root):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError("manifest input must be a directory")
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("symlinks are not supported in deliverables")
        if path.is_file():
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            files.append({"path": path.relative_to(root).as_posix(),
                          "bytes": path.stat().st_size, "sha256": digest.hexdigest()})
    if not files:
        raise ValueError("deliverables directory is empty")
    return {"schema_version": 1, "files": files}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init").add_argument("path")
    for command in ("check", "outline"):
        sub.add_parser(command).add_argument("project")
    captions = sub.add_parser("captions")
    captions.add_argument("srt")
    captions.add_argument("--duration", type=float)
    manifest = sub.add_parser("manifest")
    manifest.add_argument("directory")
    manifest.add_argument("--out", required=True)
    args = parser.parse_args()
    try:
        if args.command == "init":
            init_project(args.path)
        elif args.command in ("check", "outline"):
            data = read_json(args.project)
            errors, warnings = check_project(data)
            if args.command == "check" or errors:
                print(json.dumps({"structural_errors": errors, "warnings": warnings,
                                  "semantic_review": "not performed"}, ensure_ascii=False, indent=2))
            else:
                for scene in data["scenes"]:
                    print(f"{scene['id']} | {scene['section']} | {scene['title']}")
                    print(f"  Narration: {scene['narration']}")
                    print(f"  Transition: {scene['transition']}")
            return int(bool(errors))
        elif args.command == "captions":
            errors, warnings, count = check_captions(
                Path(args.srt).read_text(encoding="utf-8-sig"), args.duration)
            print(json.dumps({"cues": count, "errors": errors, "warnings": warnings,
                              "speech_alignment": "not checked"}, indent=2))
            return int(bool(errors))
        else:
            root, out = Path(args.directory).resolve(), Path(args.out).resolve()
            if out.is_relative_to(root):
                raise ValueError("put the manifest outside the hashed directory")
            write_json(out, make_manifest(root))
            print("Wrote SHA-256 manifest; file integrity does not establish content quality.")
    except (ValueError, OSError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
