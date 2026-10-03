#!/usr/bin/env python3
"""Offline planning, caption, and integrity helpers. No network or paid services."""
import argparse
import difflib
import hashlib
import json
import math
import os
import re
import shutil
import sys
import unicodedata
from collections import Counter
from decimal import Decimal
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
    version = data.get("schema_version")
    if isinstance(version, bool) or version != 1:
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
            errors.append(f"claim {identifier}: invalid kind {item.get('kind')!r}; "
                          "expected source, demonstration, illustration, or interpretation")
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
                errors.append(f"scene {identifier}: beat id must be nonempty text")
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
    blocks = re.split(r"\n(?:[ \t]*\n)+", text)
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


LINK_TAGS = (0xA000000C, 0xA0000003)  # Windows reparse tags: symbolic link, junction


def is_link(path):
    """True for symlinks and for Windows junctions, which is_symlink() does not report."""
    return path.is_symlink() or getattr(os.lstat(path), "st_reparse_tag", 0) in LINK_TAGS


def make_manifest(root):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError("manifest input must be a directory")
    files, pending = [], [root]
    # Walk without following links so nothing outside the directory can be hashed.
    while pending:
        for path in pending.pop().iterdir():
            if is_link(path):
                raise ValueError(f"symlinks, junctions, and other links are not supported in deliverables: "
                                 f"{path.relative_to(root).as_posix()}")
            if path.is_dir():
                pending.append(path)
            elif path.is_file():
                digest = hashlib.sha256()
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(chunk)
                files.append({"path": path.relative_to(root).as_posix(),
                              "bytes": path.stat().st_size, "sha256": digest.hexdigest()})
    if not files:
        raise ValueError("deliverables directory is empty")
    files.sort(key=lambda entry: entry["path"])
    return {"schema_version": 1, "files": files}


# Speech checks compare the intended script with a recognizer transcript of the audio.
# They locate problems for listening; they do not listen, and they cannot hear a misreading
# that the recognizer's language model turns back into the intended word.

CN_DIGITS = {"零": 0, "〇": 0, "一": 1, "二": 2, "兩": 2, "两": 2, "三": 3, "四": 4,
             "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
CN_UNITS = {"十": 10, "百": 100, "千": 1000}
CN_BIG = {"萬": 10 ** 4, "万": 10 ** 4, "億": 10 ** 8, "亿": 10 ** 8}
SCALES = {**CN_UNITS, **CN_BIG}
EN_SMALL = {word: value for value, word in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
    "fifteen sixteen seventeen eighteen nineteen".split())}
EN_TENS = {word: value * 10 for value, word in enumerate(
    "twenty thirty forty fifty sixty seventy eighty ninety".split(), 2)}
EN_BIG = {"thousand": 10 ** 3, "million": 10 ** 6, "billion": 10 ** 9}
EN_SCALE_WORDS = {"hundred": 100, **EN_BIG}
EN_ORDINALS = {"third": "three", "fourth": "four", "fifth": "five", "sixth": "six", "seventh": "seven",
               "eighth": "eight", "ninth": "nine", "tenth": "ten", "eleventh": "eleven", "twelfth": "twelve",
               **{word + "th": word for word in ("thirteen", "fourteen", "fifteen", "sixteen",
                                                  "seventeen", "eighteen", "nineteen")},
               **{word[:-1] + "ieth": word for word in EN_TENS}}
MONTHS = ("january|february|march|april|may|june|july|august|september|october|november|december"
          "|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec")
EN_NEGATIONS = {"not", "no", "never", "none", "nothing", "nobody", "neither", "nor", "without"}
ZH_NEGATIONS = "不沒未無非別勿否莫"
ZH_VARIANTS = str.maketrans({"没": "沒", "无": "無", "别": "別"})
DETERMINERS = "這这那每哪某"  # 這一題 and 這題 say the same thing; 一 there is not a quantity
# Traditional/Simplified pairs used only to warn that the two texts use different scripts.
SCRIPT_PAIRS = {pair[0] + pair[1] for pair in [
    "這这", "們们", "說说", "個个", "時时", "會会", "來来", "為为", "對对", "學学", "發发", "後后",
    "麼么", "還还", "過过", "實实", "現现", "種种", "樣样", "經经", "問问", "題题", "開开", "關关",
    "體体", "讓让", "從从", "裡里", "東东", "聽听", "應应", "與与", "語语", "數数", "點点", "誤误",
    "錯错", "動动", "電电", "話话", "給给", "進进", "邊边", "頭头", "這这", "長长", "見见", "覺觉"]}
CJK = r"぀-ヿ㐀-䶿一-鿿豈-﫿가-힯"
NUMERAL = "零〇一二兩两三四五六七八九"
ARABIC = r"(?:\d{1,3}(?:,\d{3}(?!\d))+|\d+)(?:\.\d+)?"
SPEECH_TOKEN = re.compile(
    r"(?P<time>(?<![\d:])\d{1,2}:\d{2}(?::\d{2})?(?![\d:]))"
    # A clock reading needs a real minute (零五, 十, 三十九, 09); 三點八二分 is the score 3.82.
    r"|(?P<clock>(?P<hour>\d{1,2}|二十[一二三四]?|十[一二三四五六七八九]?|[一二兩两三四五六七八九])[點点]"
    r"(?P<minute>[0-5]\d|[零〇][一二三四五六七八九]|[二三四五]?十[一二三四五六七八九]?)(?=分))"
    r"|(?P<sign>(?<![0-9a-z.)\]%‰])[-−](?=\d))"
    rf"|(?P<zhsign>[負负](?=[\d{NUMERAL}十]))"
    r"|(?P<pre>[百千]分之)"
    r"|(?P<post>[%‰])"
    rf"|(?P<run>(?:{ARABIC}(?:\s(?=[十百千萬万億亿]))?|[十百千萬万億亿]\s(?=\d)|[{NUMERAL}十百千萬万億亿])+"
    rf"(?:[點点][{NUMERAL}]+(?![十百千])[萬万億亿]?)?)"
    rf"|(?P<cjk>[{CJK}])"
    rf"|(?P<word>[^\W\d_{CJK}]+(?:'[^\W\d_{CJK}]+)*)")
MEASURE = r"\s*[個个筆笔張张位人次條条份組组萬万億亿件篇頁页層层]"  # 2048 個 is a quantity, not a year
SMALL_WORD = re.compile(r"\s+(?:" + "|".join(EN_SMALL) + r")\b")  # "point five" = 0.5
RUN_PART = re.compile(rf"(?P<arabic>{ARABIC})|[點点](?P<fraction>[{NUMERAL}]+)|(?P<char>\S)")


def number_text(value):
    """Canonical text for a number: decimals keep their written digits (3.10 ≠ 3.1); 2.0 = 2."""
    if value == value.to_integral_value():
        return format(value.to_integral_value(), "f")
    return format(value, "f")


def digit_reading(run, year=False):
    """True when a Chinese numeral run is read digit by digit as one number (二零二五, 一六零零)."""
    chars = [part.group("char") for part in RUN_PART.finditer(run)]
    return (len(chars) >= 2 and all(chars) and not any(char in SCALES or char in "兩两" for char in chars)
            and (len(chars) >= 3 or year or any(char in "零〇" for char in chars)))


def run_values(run, year=False):
    """Values in one unbroken numeral run, e.g. 一千六 → 1600, 5萬7千 → 57000, 三四十 → 3, 40."""
    parts = list(RUN_PART.finditer(run))
    chars = [part.group("char") for part in parts]
    if all(chars) and not any(char in SCALES for char in chars):
        if digit_reading(run, year):
            return [Decimal("".join(str(CN_DIGITS[char]) for char in chars))]  # 二零二五 = 2025
        return [Decimal(CN_DIGITS[char]) for char in chars]  # 兩三 = 2, 3 (a range, not 23)
    values = []
    state = {}

    def reset():
        state.update(total=Decimal(0), section=Decimal(0), number=None, single=False, unit=1,
                     zero=False, started=False)

    def finish():
        number, single = state["number"], state["single"]
        if number is not None and single and not state["zero"] and state["unit"] >= 100:
            number *= state["unit"] // 10  # 一千六 = 1600, 三萬五 = 35000
        if state["started"]:
            values.append(state["total"] + state["section"] + (number or 0))
        reset()

    reset()
    for part in parts:
        char = part.group("char")
        if part.group("arabic") or char in CN_DIGITS:
            if part.group("arabic"):
                text = part.group("arabic").replace(",", "")
                value, single = Decimal(text), len(text) == 1
            else:
                value, single = Decimal(CN_DIGITS[char]), True
            if state["number"] is not None and not (state["zero"] and state["number"] == 0):
                finish()  # 三四十 = 3, 40: a digit cannot follow a digit inside one number
            zero = state["zero"] or (char in ("零", "〇") if char else False)
            state.update(number=value, single=single, zero=zero, started=True)
        elif part.group("fraction") is not None:
            if state["number"] is None:
                state["number"], state["section"] = state["section"], Decimal(0)
            state["number"] = (state["number"] or Decimal(0)) + Decimal(
                "0." + "".join(str(CN_DIGITS[digit]) for digit in part.group("fraction")))
            state.update(single=False, started=True)
        elif char in CN_UNITS:
            state["section"] += (state["number"] if state["number"] is not None else 1) * CN_UNITS[char]
            state.update(number=None, single=False, unit=CN_UNITS[char], zero=False, started=True)
        elif char in CN_BIG:
            base = state["section"] + (state["number"] or 0)
            state["total"] += (base or 1) * CN_BIG[char]
            state.update(section=Decimal(0), number=None, single=False, unit=CN_BIG[char], zero=False,
                         started=True)
    finish()
    return values


def english_numbers(words):
    """Values in a run of English number words: 'one hundred and five' → 105, 'one two' → 1, 2."""
    values = []
    state = {}

    def reset():
        state.update(total=0, current=0, last=None, fraction=None, tens_digit=False, smallest_big=None,
                     scale=1, started=False)

    def finish():
        if state["started"]:
            value = Decimal(state["total"] + state["current"])
            fraction = (state["fraction"] or "") + ("0" if state["tens_digit"] else "")
            if fraction:
                value += Decimal("0." + fraction)
            values.append(value * state["scale"])
        reset()

    reset()
    for word in words:
        if word == "and":
            continue
        if word == "point":
            if state["fraction"] is not None:
                finish()  # a second "point" (1.2.0) starts the next component
            else:
                state.update(fraction="", started=True)
            continue
        if state["fraction"] is not None:
            small, tens = EN_SMALL.get(word), EN_TENS.get(word)
            if small is not None and state["tens_digit"] and small < 10:
                state["fraction"] += str(small)
                state["tens_digit"] = False
                continue
            if state["tens_digit"]:
                state["fraction"] += "0"
                state["tens_digit"] = False
            if small is not None:
                state["fraction"] += str(small)  # "point one three" = .13; "point twelve" = .12
                continue
            if tens is not None:
                state["fraction"] += str(tens // 10)
                state["tens_digit"] = True
                continue
            if word in EN_BIG:
                state["scale"] = EN_BIG[word]  # "one point five million"
                finish()
                continue
            finish()
        small, tens = EN_SMALL.get(word), EN_TENS.get(word)
        if small is not None:
            if state["last"] == "small" or (state["last"] == "tens" and small >= 10):
                finish()  # "one two" is two numbers; "twenty five" is one
            state["current"] += small
            state["last"] = "small"
        elif tens is not None:
            if state["last"] in ("small", "tens"):
                finish()
            state["current"] += tens
            state["last"] = "tens"
        elif word == "hundred":
            if state["current"] >= 100:  # "one hundred and five hundred" = 100, 500
                rest = state["current"] % 100
                state["current"] -= rest
                finish()
                state.update(current=rest, started=True)
            state["current"] = (state["current"] or 1) * 100
            state["last"] = "hundred"
        else:
            scale = EN_BIG[word]
            if state["smallest_big"] is not None and scale >= state["smallest_big"]:
                current = state["current"]  # "one thousand and two thousand" = 1000, 2000
                state["current"] = 0
                finish()
                state.update(current=current, started=True)
            state["total"] += (state["current"] or 1) * scale
            state.update(current=0, last="big", smallest_big=scale)
        state["started"] = True
    finish()
    return values


def normalize_speech(text):
    text = re.sub(r"\[[^\[\]\d:]{1,40}\]|【[^【】\d]{1,40}】", " ", text)  # non-speech tags: [Music], [音樂]
    text = re.sub(r"[⁰¹²³⁴-⁹₀-₉]+", lambda match: " " + match.group() + " ", text)  # 10⁶ is 10 and 6
    text = unicodedata.normalize("NFKC", text.replace("，", "、")).casefold()  # ， is never a digit group
    text = re.sub(r"(?<=[^\W\d_])[’‘ʼ`´](?=[^\W\d_])", "'", text)
    # Recognizers expand or contract freely: don't = do not, can't = cannot = can not.
    text = re.sub(r"\bcannot\b", "can not", text)
    text = re.sub(r"\b([a-z]+)n't\b", lambda m: {"ca": "can", "wo": "will", "sha": "shall"}.get(
        m.group(1), m.group(1)) + " not", text)
    # Ordinals keep a shared "th" marker: eleventh = 11th, July twenty second = July 22nd.
    text = re.sub(rf"\b({MONTHS})\s+(twenty|thirty)[\s-]+(first|second)\b",
                  lambda m: f"{m.group(1)} {m.group(2)} {'one' if m.group(3) == 'first' else 'two'} th", text)
    text = re.sub(rf"\b({MONTHS})\s+(first|second)\b",
                  lambda m: f"{m.group(1)} {'one' if m.group(2) == 'first' else 'two'} th", text)
    text = re.sub(r"\b(" + "|".join(EN_TENS) + r")[\s-]+first\b", r"\1 one th", text)
    text = re.sub(r"\b(" + "|".join(EN_ORDINALS) + r")\b", lambda m: EN_ORDINALS[m.group(1)] + " th", text)
    return text


def share_range_marks(items, text):
    """百分之八十八到九十八 = 88 到 98% = 88%-98%: one percent sign covers both ends of a range."""
    def attached(index):
        follower = items[index + 1] if index + 1 < len(items) else None
        return follower[1] if follower and follower[0] == "mark" and follower[1] in "%‰" else None

    numbers = [index for index, item in enumerate(items) if item[0] == "num"]
    inserts = []
    for first, second in zip(numbers, numbers[1:]):
        between = items[first + 1:second]
        if not all((kind == "mark" and value in "%‰") or (kind == "tok" and value in ("到", "至", "或"))
                   for kind, value, *_ in between):
            continue
        gap = re.sub(r"[%‰]|[百千]分之", "", text[items[first][3]:items[second][2]])
        if not re.fullmatch(r"\s*[到至或~～\-–—]\s*", gap) or re.match(MEASURE + "|\\s*[年倍元]", text[items[second][3]:]):
            continue  # "提升了 15%，到 2026 年" is not a range
        first_mark, second_mark = attached(first), attached(second)
        if first_mark and not second_mark:
            inserts.append((second + 1, first_mark, items[second][3]))
        elif second_mark and not first_mark:
            inserts.append((first + 1, second_mark, items[first][3]))
    for position, mark, at in sorted(inserts, reverse=True):
        items.insert(position, ["mark", mark, at, at])


def speech_items(text):
    """Return (normalized text, items); each item is [kind, value, start, end] with kind num, mark, or tok."""
    text = normalize_speech(text)
    items, pending, prefix = [], [], []

    def add(kind, value, start, end):
        items.append([kind, value, start, end])
        if kind == "num" and prefix:
            mark, mark_start, mark_end = prefix.pop()
            items.append(["mark", mark, mark_start, mark_end])  # 百分之二十九 = 29%

    def flush():
        connectors = []
        while pending and pending[-1][0] in ("and", "point"):
            connectors.insert(0, pending.pop())
        if pending:
            for value in english_numbers([word for word, _, _ in pending]):
                add("num", number_text(value), pending[0][1], pending[-1][2])
        for word, start, end in connectors:
            items.append(["tok", word, start, end])
        pending.clear()

    for match in SPEECH_TOKEN.finditer(text):
        start, end, word = match.start(), match.end(), match.group("word")
        if word:
            previous = items[-1] if items else None
            if word in EN_SCALE_WORDS and not pending and previous and previous[0] == "num" \
                    and previous[4:] == ["arabic"] and not text[previous[3]:start].strip():
                previous[1] = number_text(Decimal(previous[1]) * EN_SCALE_WORDS[word])  # 1.5 million
                previous[3] = end
                continue
            connector = (word == "point" and (pending or re.match(SMALL_WORD, text[end:]))) or (
                word == "and" and pending and pending[-1][0] in EN_SCALE_WORDS)
            if word in EN_SMALL or word in EN_TENS or word in EN_SCALE_WORDS or connector:
                if pending and re.search(r"[^\s-]", text[pending[-1][2]:start]):
                    flush()  # punctuation ends a number: "twenty-nine; one million"
                    if word in ("and", "point") and not re.match(SMALL_WORD, text[end:]):
                        items.append(["tok", word, start, end])
                        continue
                pending.append((word, start, end))  # "one hundred and five" is one number
                continue
        flush()
        if match.group("time"):
            for index, value in enumerate(int(piece) for piece in match.group("time").split(":")):
                if index == 0 or value:
                    add("num", str(value), start, end)  # 12:00 = 十二點, 3:05 = 三點零五分
        elif match.group("clock"):
            for piece in (match.group("hour"), match.group("minute")):
                values = [Decimal(piece)] if piece.isdigit() else run_values(piece)
                for value in values:
                    add("num", number_text(value), start, end)
        elif match.group("sign") or match.group("zhsign"):
            items.append(["mark", "-", start, end])
        elif match.group("pre"):
            prefix[:] = [("%" if match.group("pre")[0] == "百" else "‰", start, end)]
        elif match.group("post"):
            items.append(["mark", match.group("post"), start, end])
        elif match.group("run"):
            run = match.group("run")
            before = text[:start].rstrip()[-1:]
            if run in ("一", "1") and before and before in DETERMINERS:
                items.append(["tok", "一", start, end])
                continue
            year = text[end:end + 1] == "年"
            values = run_values(run, year)
            for value in values:
                add("num", number_text(value), start, end)
            number_item = items[-1 if items[-1][0] == "num" else -2]
            if len(values) == 1 and re.fullmatch(ARABIC, run):
                number_item.append("arabic")
            elif digit_reading(run) and not year and not (len(run) == 4 and 1900 <= values[0] <= 2099
                                                          and not re.match(MEASURE, text[end:])):
                number_item.append("digits")  # equal value, different reading (not a year): shown for listening
        elif match.group("cjk"):
            prefix.clear()
            items.append(["tok", match.group("cjk"), start, end])
        elif word:
            prefix.clear()
            previous = items[-1] if items else None
            if word in ("percent", "cent") and previous and previous[0] == "num":
                items.append(["mark", "%", start, end])
            elif word == "per" and previous and previous[0] == "num" and re.match(r"\s*cent\b", text[end:]):
                continue
            elif word in ("st", "nd", "rd", "th") and previous and previous[0] == "num":
                items.append(["tok", "th", start, end])
            else:
                items.append(["tok", word, start, end])
    flush()
    share_range_marks(items, text)
    for index, item in enumerate(items):  # "minus three" / "negative three" = -3
        if item[0] == "tok" and item[1] in ("minus", "negative") and index + 1 < len(items) \
                and items[index + 1][0] == "num" and not (index and items[index - 1][0] == "num") \
                and not (item[1] == "minus" and index and re.fullmatch(r"[a-z]", items[index - 1][1])):
            item[0], item[1] = "mark", "-"  # but "n minus one" is subtraction, like "n-1"
    return text, [item[:4] + (["digits"] if item[4:] == ["digits"] else []) for item in items]


def negation_counts(items):
    counts = Counter()
    for kind, value, *_ in items:
        if kind != "tok":
            continue
        value = value.translate(ZH_VARIANTS)
        if value in ZH_NEGATIONS:
            counts[value] += 1
        elif value in EN_NEGATIONS:
            counts["English negation"] += 1
    return counts


def written_forms(text, items, values):
    forms = {}
    for kind, value, start, end, *_ in items:
        if kind == "num" and value in values:
            forms.setdefault(value, [])
            if text[start:end] not in forms[value]:
                forms[value].append(text[start:end])
    return forms


def compare_speech(script, heard, min_similarity=None, limit=40):
    script_text, want = speech_items(script)
    heard_text, got = speech_items(heard)
    if not want:
        raise ValueError("the script contains no words or numbers to compare")
    def key(item):
        return {"num": "#", "mark": "~", "tok": ""}[item[0]] + item[1] + (":digits" if item[4:] else "")

    want_keys, got_keys = [key(item) for item in want], [key(item) for item in got]
    matcher = difflib.SequenceMatcher(None, want_keys, got_keys, autojunk=False)
    similarity = matcher.ratio()

    def passage(text, items, first, last):  # a 百分之 mark sits before its number in the text
        span = items[first:last]
        return text[min(item[2] for item in span):max(item[3] for item in span)].strip() if span else ""

    differences, script_variant, digit_readings = [], 0, []
    for tag, a1, a2, b1, b2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace":
            for a, b in zip(range(a1, a2), range(b1, b2)):
                script_variant += want_keys[a] + got_keys[b] in SCRIPT_PAIRS
                if want[a][:2] == got[b][:2] and want[a][0] == "num":
                    digit_readings.append(f"{script_text[want[a][2]:want[a][3]]} → {heard_text[got[b][2]:got[b][3]]}")
        context = want[max(0, a1 - 8):a1]  # up to eight script tokens before the change
        changed = want[a1:max(a2, a1 + 1)]
        until = min(item[2] for item in changed) if changed else len(script_text)
        after = script_text[min([item[2] for item in context] + [until]):until].strip() if context else ""
        differences.append({"change": {"delete": "missing", "insert": "extra", "replace": "replaced"}[tag],
                            "script": passage(script_text, want, a1, a2),
                            "heard": passage(heard_text, got, b1, b2), "after": after})
    numbers_want = [item[1] for item in want if item[0] == "num"]
    numbers_got = [item[1] for item in got if item[0] == "num"]
    missing = list((Counter(numbers_want) - Counter(numbers_got)).elements())
    extra = list((Counter(numbers_got) - Counter(numbers_want)).elements())
    marks_want = Counter(item[1] for item in want if item[0] == "mark")
    marks_got = Counter(item[1] for item in got if item[0] == "mark")
    neg_want, neg_got = negation_counts(want), negation_counts(got)
    warnings = []
    if script_variant:
        warnings.append("the transcript uses Simplified Chinese where the script uses Traditional "
                        f"({script_variant} aligned characters); convert one side before judging the differences")
    if digit_readings:
        warnings.append("same number read digit by digit on one side (" + "; ".join(digit_readings[:5]) +
                        "): right for codes and years, wrong for quantities; listen")
    if not got:
        warnings.append("the transcript contains no words or numbers; the audio may be silent or music only")
    if min_similarity is None:
        similarity_check = "not performed (pass --min-similarity calibrated for this recognizer)"
    else:
        similarity_check = "pass" if similarity >= min_similarity else "fail"
    report = {
        "similarity": round(similarity, 4),
        "similarity_check": similarity_check,
        "numbers": {"script": numbers_want, "heard": numbers_got, "missing": missing, "extra": extra,
                    "missing_as_written": written_forms(script_text, want, set(missing)),
                    "extra_as_written": written_forms(heard_text, got, set(extra)),
                    "check": "fail" if missing or extra else "pass"},
        "markers": {"script": dict(marks_want), "heard": dict(marks_got),
                    "check": "fail" if marks_want != marks_got else "pass"},
        "negations": {"script": dict(neg_want), "heard": dict(neg_got),
                      "check": "fail" if neg_want != neg_got else "pass"},
        "differences": differences[:limit],
        "differences_not_shown": max(0, len(differences) - limit),
        "warnings": warnings,
        "listening": "not performed; read the differences, then listen to them. Heteronyms, acronyms, and "
                     "number readings that the recognizer restores to the intended word cannot be detected here",
    }
    failed = [name for name in ("numbers", "markers", "negations") if report[name]["check"] == "fail"]
    if similarity_check == "fail":
        failed.append("similarity")
    if not got:
        failed.append("empty transcript")
    report["failed"] = failed
    return report


def read_text_argument(path, flag):
    path = Path(path)
    if path.is_dir():
        raise ValueError(f"{flag} {path} is a directory; pass a text file")
    data = path.read_bytes()
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        hint = " (it looks like UTF-16, the Windows PowerShell 5.1 '>' default)" \
            if data[:2] in (b"\xff\xfe", b"\xfe\xff") else ""
        raise ValueError(f"{flag} {path}: not UTF-8 text{hint}; save it as UTF-8") from exc


def looks_like_json(text):
    try:
        return isinstance(json.loads(text), (dict, list))
    except ValueError:
        return False


def plain_transcript(text, flag):
    stripped = text.strip()
    first_line = stripped.splitlines()[0] if stripped else ""
    if stripped.startswith("WEBVTT") or looks_like_json(stripped) or looks_like_json(first_line) \
            or re.search(r"(?m)^[ \t]*\[?[ \t]*(?:\d+:)?\d{1,2}:\d{2}[,.]\d{3}[ \t]*-->", text):
        kind = "transcript" if flag == "--heard" else "text"
        raise ValueError(f"{flag} looks like captions or recognizer JSON; pass plain {kind} "
                         "(cue numbers and timestamps would be read as spoken numbers)")
    return text


def scene_script(project_path, scene_id):
    if Path(project_path).is_dir():
        raise ValueError(f"{project_path} is a directory; pass the path to its project.json")
    data = read_json(project_path)
    scenes = data.get("scenes") if isinstance(data, dict) else None
    for scene in scenes if isinstance(scenes, list) else []:
        if isinstance(scene, dict) and scene.get("id") == scene_id:
            parts = [scene.get(key) for key in ("narration", "transition")]
            if not all(isinstance(part, str) for part in parts):
                raise ValueError(f"scene {scene_id}: narration and transition must be text")
            return "\n".join(parts)
    raise ValueError(f"scene {scene_id} not found in {project_path}")


def fraction(text):
    value = float(text)
    if not 0 <= value <= 1:
        raise argparse.ArgumentTypeError("must be between 0 and 1")
    return value


def positive_seconds(text):
    value = float(text)
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError("duration must be finite and positive")
    return value


def main():
    # Lesson text can be in any language; never let a console code page crash the report.
    # Write UTF-8 unless the user chose an encoding with PYTHONIOENCODING.
    chosen = {} if os.environ.get("PYTHONIOENCODING") else {"encoding": "utf-8"}
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace", **chosen)
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init").add_argument("path")
    for command in ("check", "outline"):
        sub.add_parser(command).add_argument("project")
    captions = sub.add_parser("captions")
    captions.add_argument("srt")
    captions.add_argument("--duration", type=positive_seconds,
                          help="measured final video duration in seconds; without it cue ends are not checked")
    manifest = sub.add_parser("manifest")
    manifest.add_argument("directory")
    manifest.add_argument("--out", required=True)
    speech = sub.add_parser("speech", help="compare a recognizer transcript with what should have been said")
    speech.add_argument("--heard", required=True,
                        help="UTF-8 plain-text recognizer transcript of the audio (not SRT/VTT/JSON)")
    source = speech.add_mutually_exclusive_group(required=True)
    source.add_argument("--script", help="UTF-8 text file: what should have been said")
    source.add_argument("--project", help="project.json; the script is --scene's narration then transition")
    speech.add_argument("--scene", help="scene ID, with --project")
    speech.add_argument("--min-similarity", type=fraction,
                        help="threshold calibrated on known good and bad takes for this recognizer")
    args = parser.parse_args()
    try:
        if args.command == "init":
            init_project(args.path)
        elif args.command in ("check", "outline"):
            if Path(args.project).is_dir():
                raise ValueError(f"{args.project} is a directory; pass the path to its project.json")
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
            errors, warnings, count = check_captions(read_text_argument(args.srt, "srt"), args.duration)
            print(json.dumps({"cues": count, "errors": errors, "warnings": warnings,
                              "duration_check": "performed" if args.duration is not None
                              else "not performed (pass --duration)",
                              "speech_alignment": "not checked"}, ensure_ascii=False, indent=2))
            return int(bool(errors))
        elif args.command == "speech":
            if args.project and not args.scene:
                raise ValueError("--project needs --scene")
            if args.scene and not args.project:
                raise ValueError("--scene needs --project")
            script = (scene_script(args.project, args.scene) if args.project
                      else plain_transcript(read_text_argument(args.script, "--script"), "--script"))
            heard = plain_transcript(read_text_argument(args.heard, "--heard"), "--heard")
            report = compare_speech(script, heard, args.min_similarity)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return int(bool(report["failed"]))
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
