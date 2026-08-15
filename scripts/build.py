#!/usr/bin/env python3
"""Build the first-pass Dream of the Red Chamber parallel edition.

Chinese source: zh/github-huangtuzhi/chapter-1 ... chapter-120.
It is selected because it is already a complete, clean 120-chapter corpus.

English source: en/bencraft/gutenberg-bencraft-1.txt and -2.txt.
These checked-in Gutenberg/Joly files cover chapters 1-56. Later chapters are
represented with Chinese only and an explicit source-missing note in the
alignment data; the script does not invent English.
"""

from __future__ import annotations

import json
import math
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZH_DIR = ROOT / "zh" / "github-huangtuzhi"
EN_FILES = [
    ROOT / "en" / "bencraft" / "gutenberg-bencraft-1.txt",
    ROOT / "en" / "bencraft" / "gutenberg-bencraft-2.txt",
]
DATA_DIR = ROOT / "data"
BOOK_ONE = ROOT / "01-book-one"
BOOK_TWO = ROOT / "02-book-two"


ROMAN = {
    "I": 1,
    "V": 5,
    "X": 10,
    "L": 50,
    "C": 100,
}

ABBREVIATIONS = {
    "Mr.",
    "Mrs.",
    "Ms.",
    "Dr.",
    "St.",
    "H.B.M.",
    "etc.",
    "e.g.",
    "i.e.",
    "No.",
}


@dataclass
class Segment:
    text: str
    index: int
    start: int
    end: int


NAME_ANCHORS = {
    "甄士隐": ("Chen Shih-yin", "Shih-yin"),
    "贾雨村": ("Chia Yü-ts'un", "Yü-ts'un"),
    "林黛玉": ("Lin Tai-yü", "Tai-yü"),
    "贾宝玉": ("Chia Pao-yü", "Pao-yü"),
    "薛宝钗": ("Hsüeh Pao-ch'ai", "Pao-ch'ai"),
    "王熙凤": ("Wang Hsi-feng", "Hsi-feng"),
    "刘姥姥": ("old goody Liu", "Goody Liu", "Liu"),
    "大观园": ("Ta Kuan", "Prospect Garden"),
    "太虚幻境": ("Great Void", "Illusory Land"),
    "通灵宝玉": ("Precious Jade", "Spiritual Jade"),
    "妙玉": ("Miao-yü",),
    "香菱": ("Hsiang-ling",),
    "晴雯": ("Ch'ing-wen",),
    "袭人": ("Hsi Jen", "Hsi-jen"),
    "探春": ("T'an-ch'un",),
    "宝琴": ("Pao-ch'in",),
}

ZH_SENTENCE_END_RE = re.compile(r".+?[。！？]+[”’』」》）\])]*|.+$", re.S)


def roman_to_int(s: str) -> int:
    total = 0
    prev = 0
    for ch in reversed(s.upper()):
        val = ROMAN[ch]
        if val < prev:
            total -= val
        else:
            total += val
            prev = val
    return total


def normalize_spaces(s: str) -> str:
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def read_zh_chapters() -> dict[int, str]:
    chapters: dict[int, str] = {}
    for n in range(1, 121):
        path = ZH_DIR / f"chapter-{n}"
        text = path.read_text(encoding="utf-8", errors="replace")
        text = text.replace("\ufeff", "")
        lines = [line.strip() for line in text.splitlines()]
        lines = [line for line in lines if line]
        if lines and re.search(r"第\s*\d+\s*章", lines[0]):
            lines = lines[1:]
        text = "\n".join(lines)
        text = re.sub(r"\[\(?|\)?\]", "", text)
        text = text.replace("?", "？")
        chapters[n] = normalize_spaces(text)
    return chapters


def strip_gutenberg(text: str) -> str:
    start = re.search(r"\*\*\* START OF THE PROJECT GUTENBERG EBOOK.*?\*\*\*", text)
    if start:
        text = text[start.end() :]
    end = re.search(r"\*\*\* END OF THE PROJECT GUTENBERG EBOOK", text)
    if end:
        text = text[: end.start()]
    text = re.sub(r"Produced by .*?(?=\n\n)", "", text, flags=re.S)
    return normalize_spaces(text)


def read_en_chapters() -> dict[int, str]:
    chapters: dict[int, str] = {}
    chapter_re = re.compile(r"(?m)^CHAPTER\s+([IVXLC]+)\.?\s*$")
    for path in EN_FILES:
        text = strip_gutenberg(path.read_text(encoding="utf-8", errors="replace"))
        matches = list(chapter_re.finditer(text))
        for i, match in enumerate(matches):
            n = roman_to_int(match.group(1))
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[start:end]
            body = re.sub(r"\n\s*\n", "\n\n", body)
            lines = body.splitlines()
            while lines and not lines[0].strip():
                lines.pop(0)
            # Drop the short translated chapter couplet at the top.
            while lines and lines[0].strip() and len(lines[0].strip()) < 90:
                lines.pop(0)
            while lines and not lines[0].strip():
                lines.pop(0)
            chapters[n] = normalize_spaces("\n".join(lines))
    return chapters


def split_zh(text: str) -> list[Segment]:
    segments: list[Segment] = []
    for match in ZH_SENTENCE_END_RE.finditer(text):
        raw = match.group(0)
        stripped = raw.strip()
        if not stripped:
            continue
        start = match.start() + len(raw) - len(raw.lstrip())
        end = match.end() - len(raw) + len(raw.rstrip())
        segments.append(Segment(text=stripped, index=len(segments), start=start, end=end))
    return segments


def split_en(text: str) -> list[Segment]:
    text = re.sub(r"\s+", " ", text).strip()
    pieces: list[tuple[str, int, int]] = []
    start = 0
    for i, ch in enumerate(text):
        if ch not in ".!?;:,":
            continue
        token = text[max(0, i - 12) : i + 1].split()[-1]
        if token in ABBREVIATIONS or re.fullmatch(r"(?:[A-Z]\.)+", token):
            continue
        j = i + 1
        while j < len(text) and text[j] in "\"')]}”’":
            j += 1
        if j < len(text) and not text[j].isspace():
            continue
        piece = text[start:j].strip()
        if piece:
            offset = len(text[start:j]) - len(text[start:j].lstrip())
            pieces.append((piece, start + offset, j))
        start = j
    tail = text[start:].strip()
    if tail:
        offset = len(text[start:]) - len(text[start:].lstrip())
        pieces.append((tail, start + offset, len(text)))
    return merge_tiny(pieces, min_len=24, max_len=180)


def merge_tiny(pieces: list[tuple[str, int, int]], min_len: int, max_len: int) -> list[Segment]:
    merged: list[tuple[str, int, int]] = []
    buf = ""
    buf_start = 0
    buf_end = 0
    for piece, start, end in pieces:
        if not buf:
            buf = piece
            buf_start = start
            buf_end = end
        elif len(buf) < min_len and len(buf) + 1 + len(piece) < max_len:
            buf = f"{buf} {piece}"
            buf_end = end
        else:
            merged.append((buf, buf_start, buf_end))
            buf = piece
            buf_start = start
            buf_end = end
    if buf:
        merged.append((buf, buf_start, buf_end))
    return [Segment(text=p, index=i, start=start, end=end) for i, (p, start, end) in enumerate(merged)]


def char_mass(text: str) -> int:
    latin = sum(1 for ch in text if ch.isascii() and ch.isalpha())
    han = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    other = sum(1 for ch in text if not ch.isspace()) - latin - han
    return han * 2 + latin + other


def prefix_masses(segments: list[Segment]) -> list[int]:
    masses = [0]
    total = 0
    for segment in segments:
        total += char_mass(segment.text)
        masses.append(total)
    return masses


def semantic_bonus(zh_text: str, en_text: str) -> float:
    en_folded = en_text.casefold()
    bonus = 0.0
    for zh_anchor, en_anchors in NAME_ANCHORS.items():
        if zh_anchor not in zh_text:
            continue
        if any(anchor.casefold() in en_folded for anchor in en_anchors):
            bonus += 0.18
        else:
            bonus -= 0.08
    return bonus


def english_span_text(en: list[Segment], start: int, end: int) -> str:
    return " ".join(s.text for s in en[start:end]).strip()


def alignment_score(
    zh: list[Segment],
    en: list[Segment],
    zh_prefix: list[int],
    en_prefix: list[int],
    zi: int,
    ei: int,
    ec: int,
) -> float:
    total_zh = zh_prefix[-1] or 1
    total_en = en_prefix[-1] or 1
    z_share = (zh_prefix[zi + 1] - zh_prefix[zi]) / total_zh
    e_share = (en_prefix[ei + ec] - en_prefix[ei]) / total_en if ec else 0.0
    z_next = zh_prefix[zi + 1] / total_zh
    e_next = en_prefix[ei + ec] / total_en if en else 1.0
    position = abs(z_next - e_next)
    if ec:
        ratio = abs(math.log((e_share + 0.0001) / (z_share + 0.0001)))
        grouping = 0.012 * max(0, ec - 1) ** 2
        empty = 0.0
    else:
        ratio = 1.0
        grouping = 0.0
        empty = 0.28
    text_bonus = semantic_bonus(zh[zi].text, english_span_text(en, ei, ei + ec)) if ec else 0.0
    return position * 2.4 + ratio * 0.24 + grouping + empty - text_bonus


def align_chapter(chapter: int, zh: list[Segment], en: list[Segment]) -> list[dict]:
    if not en:
        return [
            {
                "book": 1 if chapter <= 80 else 2,
                "chapter": chapter,
                "verse": i + 1,
                "zh": seg.text,
                "en": "",
                "source_profile": "Redactor" if chapter > 80 else "Author",
                "confidence": 0.0,
                "zh_indices": [seg.index],
                "zh_start": seg.start,
                "zh_end": seg.end,
                "en_indices": [],
                "en_start": None,
                "en_end": None,
                "note": "English source not present in checked-in Bencraft/Joly files.",
            }
            for i, seg in enumerate(zh)
        ]

    max_en_span = 8
    beam_width = 90
    zh_prefix = prefix_masses(zh)
    en_prefix = prefix_masses(en)
    n = len(zh)
    m = len(en)
    costs: list[dict[int, tuple[float, int | None]]] = [{0: (0.0, None)}]
    for zi in range(n):
        current = costs[-1]
        next_costs: dict[int, tuple[float, int | None]] = {}
        remaining_zh_after = n - zi - 1
        for ei, (base_cost, _) in current.items():
            min_ec = max(0, m - ei - remaining_zh_after * max_en_span)
            max_ec = min(max_en_span, m - ei)
            for ec in range(min_ec, max_ec + 1):
                if ec == 0 and remaining_zh_after == 0 and ei < m:
                    continue
                score = base_cost + alignment_score(zh, en, zh_prefix, en_prefix, zi, ei, ec)
                ej = ei + ec
                previous = next_costs.get(ej)
                if previous is None or score < previous[0]:
                    next_costs[ej] = (score, ei)
        if zi < n - 1 and len(next_costs) > beam_width:
            expected = m * ((zi + 1) / n)
            ranked = sorted(
                next_costs.items(),
                key=lambda item: item[1][0] + 0.015 * abs(item[0] - expected),
            )
            next_costs = dict(ranked[:beam_width])
        costs.append(next_costs)

    if m not in costs[-1]:
        raise AssertionError(f"chapter {chapter} alignment failed to consume English")

    spans: list[tuple[int, int]] = []
    ei = m
    for zi in range(n, 0, -1):
        _, prev_ei = costs[zi][ei]
        assert prev_ei is not None
        spans.append((prev_ei, ei))
        ei = prev_ei
    spans.reverse()

    rows: list[dict] = []
    total_zh = zh_prefix[-1] or 1
    total_en = en_prefix[-1] or 1
    for verse, (seg, (en_start_i, en_end_i)) in enumerate(zip(zh, spans), start=1):
        eg = en[en_start_i:en_end_i]
        zh_text = seg.text
        en_text = english_span_text(en, en_start_i, en_end_i)
        z_share = char_mass(zh_text) / total_zh
        e_share = sum(char_mass(s.text) for s in eg) / total_en if eg else 0
        confidence = max(0.05, min(0.95, 1.0 - abs(z_share - e_share) * 16 - (0.04 * max(0, len(eg) - 1)) - (0.2 if not eg else 0)))
        rows.append(
            {
                "book": 1 if chapter <= 80 else 2,
                "chapter": chapter,
                "verse": verse,
                "zh": zh_text,
                "en": en_text,
                "source_profile": "Redactor" if chapter > 80 else "Author",
                "confidence": round(confidence, 3),
                "zh_indices": [seg.index],
                "zh_start": seg.start,
                "zh_end": seg.end,
                "en_indices": [s.index for s in eg],
                "en_start": eg[0].start if eg else None,
                "en_end": eg[-1].end if eg else None,
            }
        )
    return rows


def tex_escape(s: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in s)


def wrap_macro(name: str, text: str, width: int = 76) -> str:
    if not text:
        return f"\\{name}{{}}"
    wrapped = textwrap.wrap(tex_escape(text), width=width, break_long_words=False, break_on_hyphens=False)
    return "\\%s{%s}" % (name, ("\n        ").join(wrapped))


def emit_tex(rows_by_chapter: dict[int, list[dict]]) -> None:
    for d in (BOOK_ONE, BOOK_TWO):
        d.mkdir(exist_ok=True)
        for old in d.glob("*.tex"):
            old.unlink()
    for chapter, rows in rows_by_chapter.items():
        out_dir = BOOK_ONE if chapter <= 80 else BOOK_TWO
        path = out_dir / f"{chapter:03d}.tex"
        lines = [f"\\Chapter{{{chapter}}}", ""]
        for row in rows:
            prefix = "R" if row["source_profile"] == "Redactor" else "A"
            en = row["en"] or "[English source not present in the checked-in Bencraft/Joly files.]"
            lines.extend(
                [
                    f"\\Verse{{{row['verse']}}}",
                    "{",
                    f"    {wrap_macro('z' + prefix, row['zh'])}",
                    "}",
                    "{",
                    f"    {wrap_macro('e' + prefix, en)}",
                    "}",
                    "{",
                    "}",
                    "",
                ]
            )
        path.write_text("\n".join(lines), encoding="utf-8")


def emit_master() -> None:
    includes_1 = "\n".join(f"\\include{{01-book-one/{n:03d}}}" for n in range(1, 81))
    includes_2 = "\n".join(f"\\include{{02-book-two/{n:03d}}}" for n in range(81, 121))
    master = f"""%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% We The Nameless Dream %%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\\def\\ConfigTheme{{dark}}
\\def\\ConfigCommentary{{true}}
\\def\\ConfigTrue{{true}}
\\newif\\ifConfigCommentaryOn
\\ifx\\ConfigCommentary\\ConfigTrue\\ConfigCommentaryOntrue\\else\\ConfigCommentaryOnfalse\\fi

\\documentclass[11pt]{{book}}
\\usepackage[paperwidth=7in,paperheight=10in,twoside,inner=0.8in,outer=0.45in,top=0.55in,bottom=0.75in,includefoot]{{geometry}}
\\usepackage[no-math]{{fontspec}}
\\usepackage{{luatexja-fontspec}}
\\usepackage{{titlesec}}
\\usepackage{{tocloft}}
\\usepackage{{xcolor}}
\\usepackage{{colortbl}}
\\usepackage{{setspace}}
\\usepackage{{fancyhdr}}
\\usepackage{{xparse}}
\\usepackage{{ragged2e}}
\\usepackage{{needspace}}
\\usepackage{{graphicx}}
\\usepackage{{multicol}}
\\usepackage[hidelinks]{{hyperref}}
\\usepackage{{luacolor}}
\\usepackage{{lua-ul}}

\\newcommand{{\\LocalFontPath}}{{./fonts/}}
\\setmainfont{{FreeSerif}}
\\setmainjfont[Path=\\LocalFontPath,Renderer=HarfBuzz,Scale=0.94]{{cjk-noto-serif-tc.otf}}
\\newfontfamily\\EnglishFont{{FreeSerif}}
\\newfontfamily\\TitleFont[Path=\\LocalFontPath,Scale=1.22]{{english-im-fell-english-sc-regular.ttf}}
\\newjfontfamily\\ChineseFont[Path=\\LocalFontPath,Renderer=HarfBuzz,Scale=0.94]{{cjk-noto-serif-tc.otf}}
\\let\\emph\\textsl

\\setlength{{\\parindent}}{{0pt}}
\\setlength{{\\parskip}}{{0.5em}}
\\setlength{{\\footskip}}{{24pt}}
\\setlength{{\\headheight}}{{26pt}}
\\setlength{{\\emergencystretch}}{{2em}}
\\onehalfspacing
\\raggedbottom

\\newlength{{\\VerseGap}}
\\newlength{{\\VerseRuleWidth}}
\\newlength{{\\VerseColWidth}}
\\setlength{{\\VerseGap}}{{0.75em}}
\\setlength{{\\VerseRuleWidth}}{{0.2pt}}
\\setlength{{\\VerseColWidth}}{{\\dimexpr(\\textwidth-\\VerseGap-\\VerseRuleWidth-\\VerseGap)/2\\relax}}

\\definecolor{{bg}}{{HTML}}{{2d353b}}
\\definecolor{{fg}}{{HTML}}{{e8e2d2}}
\\definecolor{{ObsGreen}}{{HTML}}{{87bb87}}
\\definecolor{{ObsBlue}}{{HTML}}{{7f9fcf}}
\\definecolor{{ObsRed}}{{HTML}}{{e67e80}}
\\definecolor{{ObsGray}}{{HTML}}{{9aa79d}}
\\colorlet{{TextColor}}{{fg}}
\\colorlet{{RuleColor}}{{fg!45!bg}}
\\colorlet{{AuthorColor}}{{ObsGreen!87!fg}}
\\colorlet{{AuthorBgColor}}{{AuthorColor!18!bg}}
\\colorlet{{RedactorColor}}{{ObsBlue!78!bg}}
\\colorlet{{RedactorBgColor}}{{RedactorColor!14!bg}}
\\colorlet{{MissingColor}}{{ObsGray!80!fg}}
\\pagecolor{{bg}}
\\AtBeginDocument{{\\color{{TextColor}}}}

\\arrayrulecolor{{RuleColor}}
\\renewcommand{{\\cfttoctitlefont}}{{\\EnglishFont\\color{{TextColor}}\\Huge\\bfseries}}
\\renewcommand{{\\cftchapfont}}{{\\EnglishFont\\color{{TextColor}}}}
\\renewcommand{{\\cftchappagefont}}{{\\EnglishFont\\color{{TextColor}}}}

\\newcommand{{\\SourceProfilePlainText}}[1]{{#1}}
\\let\\SourceProfileTextWrapper\\SourceProfilePlainText
\\newcommand{{\\SourceBgColor}}{{RedactorBgColor}}
\\newcommand{{\\SourceBackground}}[1]{{\\def\\SourceBgColor{{#1}}}}
\\newcommand{{\\SourceProfileHighlightedText}}[1]{{\\highLight[\\SourceBgColor]{{#1}}}}
\\DeclareRobustCommand{{\\Redactor}}{{\\let\\SourceProfileTextWrapper\\SourceProfileHighlightedText}}

\\NewDocumentCommand{{\\ApplyEnglishSourceProfile}}{{ m +m }}{{{{\\let\\SourceProfileTextWrapper\\SourceProfilePlainText #1\\SourceProfileTextWrapper{{#2}}}}}}
\\NewDocumentCommand{{\\ApplyChineseSourceProfile}}{{ m +m }}{{{{\\ChineseFont\\let\\SourceProfileTextWrapper\\SourceProfilePlainText #1\\SourceProfileTextWrapper{{#2}}}}}}
\\newcommand{{\\AuthorStyle}}{{\\SourceBackground{{AuthorBgColor}}\\color{{AuthorColor}}\\mdseries}}
\\newcommand{{\\RedactorStyle}}{{\\SourceBackground{{RedactorBgColor}}\\color{{RedactorColor}}\\Redactor\\mdseries}}
\\newcommand{{\\eA}}[1]{{\\ApplyEnglishSourceProfile{{\\EnglishFont\\AuthorStyle}}{{#1}}}}
\\newcommand{{\\zA}}[1]{{\\ApplyChineseSourceProfile{{\\AuthorStyle}}{{#1}}}}
\\newcommand{{\\eR}}[1]{{\\ApplyEnglishSourceProfile{{\\EnglishFont\\RedactorStyle}}{{#1}}}}
\\newcommand{{\\zR}}[1]{{\\ApplyChineseSourceProfile{{\\RedactorStyle}}{{#1}}}}
\\newcommand{{\\eP}}[1]{{\\eA{{#1}}}}
\\newcommand{{\\zP}}[1]{{\\zA{{#1}}}}

\\newcommand{{\\SourceLegendHeader}}{{{{\\large \\eA{{A}}\\quad\\eR{{R}}}}}}
\\pagestyle{{fancy}}
\\fancyhf{{}}
\\fancyhead[C]{{\\color{{TextColor}}\\hbox to 0pt{{\\hss\\SourceLegendHeader\\hss}}}}
\\fancyhead[LE]{{\\color{{TextColor}}\\nouppercase{{\\rightmark}}}}
\\fancyhead[RO]{{\\color{{TextColor}}\\nouppercase{{\\rightmark}}}}
\\fancyfoot[C]{{\\color{{TextColor}}\\thepage}}
\\fancypagestyle{{plain}}{{\\fancyhf{{}}\\fancyfoot[C]{{\\color{{TextColor}}\\thepage}}\\renewcommand{{\\headrulewidth}}{{0pt}}}}
\\renewcommand{{\\headrule}}{{{{\\color{{RuleColor}}\\hrule width\\headwidth height\\headrulewidth \\vskip-\\headrulewidth}}}}
\\renewcommand{{\\footrule}}{{{{\\color{{RuleColor}}\\hrule width\\headwidth height\\footrulewidth \\vskip-\\footrulewidth}}}}

\\newcommand{{\\ManualFrontMatterPage}}[1]{{\\clearpage\\thispagestyle{{empty}}#1\\clearpage}}
\\newcommand{{\\wetitlepage}}{{%
  \\clearpage\\newgeometry{{left=2.13cm,right=2.13cm,top=2.13cm,bottom=2.13cm}}\\pagestyle{{empty}}
  \\begin{{center}}
  \\vspace*{{0.18\\textheight}}
  {{\\fontsize{{100}}{{120}}\\fontfamily{{lmr}}\\selectfont\\textsc{{We}}\\par}}
  \\vspace*{{0.16\\textheight}}
  {{\\fontsize{{25}}{{30}}\\fontfamily{{lmr}}\\selectfont\\textrm{{The Nameless}}\\par}}
  \\vspace*{{\\fill}}
  {{\\TitleFont\\fontsize{{24}}{{30}}\\selectfont Dream of the Red Chamber\\par}}
  \\vspace*{{0.7in}}
  \\end{{center}}\\newpage\\restoregeometry\\pagestyle{{fancy}}}}
\\newcommand{{\\WeContentsPage}}{{\\clearpage\\newgeometry{{left=2.13cm,right=2.13cm,top=2.13cm,bottom=2.13cm}}\\phantomsection\\hypertarget{{tableofcontents}}{{}}\\tableofcontents\\newpage\\restoregeometry}}

\\newcommand{{\\LegendColumns}}[2]{{\\def\\LegendLeftWidth{{#1}}\\def\\LegendRightWidth{{#2}}}}
\\newcommand{{\\LegendRow}}[2]{{\\noindent\\begin{{minipage}}[t]{{\\LegendLeftWidth}}\\vspace{{0pt}}\\RaggedRight #1\\end{{minipage}}\\hfill\\begin{{minipage}}[t]{{\\LegendRightWidth}}\\vspace{{0pt}}\\RaggedRight #2\\end{{minipage}}\\par\\vspace{{0.8em}}}}
\\newcommand{{\\SourceLegendPage}}{{\\ManualFrontMatterPage{{%
  \\begin{{center}}{{\\scshape\\large The Sources}}\\\\[0.2em]{{\\itshape\\normalsize provisional}}\\\\[0.45em]{{\\LARGE We: The Nameless}}\\\\[0.45em]{{\\footnotesize\\eA{{Author}}\\quad\\eR{{Redactor}}}}\\end{{center}}
  \\begingroup\\footnotesize\\LegendColumns{{0.24\\linewidth}}{{0.70\\linewidth}}
  \\LegendRow{{\\eA{{Author}}}}{{\\eA{{Primary authorial and narrative stratum. This first-pass edition uses this profile for chapters 1--80 and for ordinary narrative material without making a settled historical claim.}}}}
  \\LegendRow{{\\eR{{Redactor}}}}{{\\eR{{Later editing, continuation, framing, and redactional visualization. Chapters 81--120 are provisionally marked this way to keep the received Honglou Meng development visible without pretending the analysis is complete.}}}}
  \\LegendRow{{\\zA{{石頭記}}}}{{\\zA{{Future work can distinguish layers associated with 石頭記 / Shi Tou Ji, later editing, and development into the received 紅樓夢 / Honglou Meng.}}}}
  \\endgroup}}}}

\\titleformat{{\\chapter}}[display]{{\\normalfont\\huge\\bfseries}}{{\\chaptername\\ \\thechapter}}{{0.5em}}{{}}
\\titleformat{{\\section}}{{\\Large\\bfseries}}{{\\thesection}}{{0.75em}}{{}}
\\newcommand{{\\BookHeading}}[1]{{\\chapter*{{#1}}}}
\\newcommand{{\\ChapterHeading}}[1]{{\\section*{{#1}}}}
\\DeclareRobustCommand{{\\TableOfContentsLink}}[1]{{\\hyperlink{{tableofcontents}}{{#1}}}}
\\DeclareRobustCommand{{\\BookTitleLink}}[1]{{\\hyperlink{{book.\\CurrentTitleBook}}{{#1}}}}
\\DeclareRobustCommand{{\\ChapterTitleText}}[1]{{\\BookTitleLink{{\\CurrentBook\\ #1}}}}
\\newcommand{{\\ChapterLink}}[1]{{\\hyperlink{{chapter.\\CurrentBook.#1}}{{\\color{{TextColor}}#1}}}}
\\newcount\\ChapterLinkIndex
\\newcount\\ChapterLinkColumnIndex
\\newcommand{{\\ChapterLinkRange}}[2]{{\\ChapterLinkIndex=#1\\relax\\ChapterLinkColumnIndex=1\\relax\\loop\\makebox[0.19\\linewidth][c]{{\\ChapterLink{{\\the\\ChapterLinkIndex}}}}\\ifnum\\ChapterLinkColumnIndex=5\\par\\nobreak\\vspace{{0.55em}}\\ChapterLinkColumnIndex=0\\fi\\advance\\ChapterLinkColumnIndex by 1\\advance\\ChapterLinkIndex by 1\\ifnum\\ChapterLinkIndex<\\numexpr#2+1\\relax\\repeat}}
\\newcommand{{\\Book}}[3]{{\\def\\CurrentTitleBook{{#1}}\\def\\CurrentBook{{#1}}\\BookHeading{{\\TableOfContentsLink{{#1}}}}\\phantomsection\\hypertarget{{book.#1}}{{}}\\addcontentsline{{toc}}{{chapter}}{{#1}}\\par\\nobreak\\medskip{{\\centering\\large #2\\par\\smallskip\\ChapterLinkRange{{#2}}{{#3}}\\par}}\\medskip}}
\\newcommand{{\\Chapter}}[1]{{\\hypertarget{{chapter.\\CurrentBook.#1}}{{}}\\ChapterHeading{{\\ChapterTitleText{{#1}}}}\\def\\CurrentChapter{{#1}}\\markboth{{\\CurrentBook\\ #1}}{{\\CurrentBook\\ #1}}}}

\\def\\englishsize{{\\normalsize}}
\\def\\chinesesize{{\\normalsize}}
\\newcommand{{\\nl}}{{\\ifhmode\\unskip\\penalty-500\\hskip 0.333em plus 0.167em minus 0.111em\\relax\\fi}}
\\newcommand{{\\VerseEnglishAtWidth}}[2]{{\\begin{{minipage}}[t]{{#1}}\\EnglishFont\\englishsize\\raggedright #2\\par\\end{{minipage}}}}
\\newcommand{{\\VerseChineseAtWidth}}[2]{{\\begin{{minipage}}[t]{{#1}}\\ChineseFont\\chinesesize\\RaggedRight #2\\par\\end{{minipage}}}}
\\newcommand{{\\VerseColumns}}[2]{{\\noindent\\VerseEnglishAtWidth{{\\VerseColWidth}}{{#1}}\\hspace{{\\VerseGap}}{{\\color{{RuleColor}}\\vrule width \\VerseRuleWidth}}\\hspace{{\\VerseGap}}\\VerseChineseAtWidth{{\\VerseColWidth}}{{#2}}\\par}}
\\newcommand{{\\VerseRule}}{{{{\\color{{RuleColor}}\\hrule}}}}
\\newcommand{{\\Verse}}[4]{{\\par\\vspace{{0.8em}}\\Needspace{{6\\baselineskip}}\\VerseRule\\vspace{{0.25em}}{{\\centering \\large \\hyperlink{{chapter.\\CurrentBook.\\CurrentChapter}}{{\\CurrentBook\\ \\CurrentChapter:#1}}\\par}}\\vspace{{0.8em}}\\VerseRule\\vspace{{0.3em}}\\begingroup\\hbadness=10000\\hfuzz=3em\\VerseColumns{{#3}}{{#2}}\\endgroup\\vspace{{0.8em}}\\ifConfigCommentaryOn\\begingroup\\hbadness=10000\\hfuzz=3em#4\\par\\endgroup\\vspace{{0.8em}}\\fi}}

\\begin{{document}}
\\frontmatter
\\hypersetup{{pageanchor=false}}
\\pagenumbering{{gobble}}
\\pagestyle{{empty}}
\\wetitlepage
\\WeContentsPage
\\SourceLegendPage
\\mainmatter
\\hypersetup{{pageanchor=true}}
\\pagestyle{{fancy}}
\\Book{{石頭記}}{{1}}{{80}}
{includes_1}
\\Book{{後四十回}}{{81}}{{120}}
{includes_2}
\\end{{document}}
"""
    (ROOT / "master.tex").write_text(master, encoding="utf-8")


def emit_readme(en_chapters: dict[int, str]) -> None:
    readme = f"""# We the Nameless: Dream of the Red Chamber

This repository is a first-pass We the Nameless edition of *Dream of the Red Chamber* / *Honglou Meng* / *Shi Tou Ji*.

It is modeled on the local `BIBLE/` reference project, but the root project is independently buildable. The extracted pieces are the page geometry, title/frontmatter identity, source-profile highlighting, and side-by-side verse system.

## Sources

Chinese uses `zh/github-huangtuzhi/chapter-1` through `chapter-120`, selected because it is already a complete 120-chapter corpus with clean chapter files.

English uses the checked-in H. Bencraft Joly Project Gutenberg files under `en/bencraft/`. Those files currently contain chapters 1-{max(en_chapters) if en_chapters else 0}; chapters after that are represented with Chinese text and explicit source-missing English placeholders. No missing English has been translated or invented.

## Generation

Run:

```sh
make data
make
```

`scripts/build.py` parses both source corpora, segments Chinese on sentence punctuation, segments English with a lightweight abbreviation-aware splitter, and produces monotonic verse-like alignment records in `data/alignment.jsonl`.

Chinese `。` is the preferred prose verse boundary. The aligner keeps Chinese sentence units short by default and lets each Chinese verse absorb the best nearby English span. The English side may therefore contain a fragment, a full sentence, several fragments, or no clean English unit when the sources do not line up neatly.

The alignment is provisional. It uses a monotonic dynamic-programming pass over Chinese sentence units and neighboring English spans, with cumulative position, length balance, and a small curated name/term table as signals. It is meant to produce a complete editable edition, not a final scholarly alignment.

Correct alignments in `data/alignment.jsonl` or improve `scripts/build.py`, then regenerate with `make data`.

Run regression checks with:

```sh
make check
```

The pytest suite in `tests/` checks source preservation, monotonic source spans, short Chinese verse boundaries, chapter boundary anchors, and curated bilingual anchors. Add a known-good correspondence by extending the anchor tables in `tests/test_alignment.py` after confirming the Chinese and English wording in the source files.

## Source Profiles

The TeX source profiles are functional now:

- `\\eA{{...}}` and `\\zA{{...}}` mark the provisional Author profile.
- `\\eR{{...}}` and `\\zR{{...}}` mark the provisional Redactor / editor / continuation profile.

This first pass marks chapters 1-80 as Author and chapters 81-120 as Redactor to visualize the traditional authorship/editorial problem cautiously.
"""
    (ROOT / "README.md").write_text(readme, encoding="utf-8")


def validate(rows_by_chapter: dict[int, list[dict]], zh_chapters: dict[int, str], en_chapters: dict[int, str]) -> None:
    assert set(rows_by_chapter) == set(range(1, 121)), "expected chapters 1-120"
    for n in range(1, 121):
        rows = rows_by_chapter[n]
        assert rows, f"chapter {n} has no verses"
        assert [r["verse"] for r in rows] == list(range(1, len(rows) + 1)), f"chapter {n} verse sequence broken"
        tex_path = (BOOK_ONE if n <= 80 else BOOK_TWO) / f"{n:03d}.tex"
        assert tex_path.exists(), f"missing {tex_path}"
        zh_join = re.sub(r"\s+", "", "".join(r["zh"] for r in rows))
        zh_src = re.sub(r"\s+", "", zh_chapters[n])
        assert len(zh_join) >= len(zh_src) * 0.96, f"chapter {n} lost too much Chinese"
        if n in en_chapters:
            en_join = re.sub(r"\s+", "", "".join(r["en"] for r in rows))
            en_src = re.sub(r"\s+", "", en_chapters[n])
            assert len(en_join) >= len(en_src) * 0.94, f"chapter {n} lost too much English"
    assert any(r["source_profile"] == "Author" for rows in rows_by_chapter.values() for r in rows)
    assert any(r["source_profile"] == "Redactor" for rows in rows_by_chapter.values() for r in rows)


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    zh_chapters = read_zh_chapters()
    en_chapters = read_en_chapters()
    rows_by_chapter: dict[int, list[dict]] = {}
    with (DATA_DIR / "alignment.jsonl").open("w", encoding="utf-8") as fh:
        for n in range(1, 121):
            rows = align_chapter(n, split_zh(zh_chapters[n]), split_en(en_chapters.get(n, "")))
            rows_by_chapter[n] = rows
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    (DATA_DIR / "source-readme.md").write_text(
        "Chinese source: zh/github-huangtuzhi, selected for complete 120-chapter structure.\n"
        f"English source: en/bencraft Gutenberg/Joly files, parsed chapters 1-{max(en_chapters)}.\n"
        "Later English is intentionally marked source-missing rather than invented.\n",
        encoding="utf-8",
    )
    emit_tex(rows_by_chapter)
    emit_master()
    emit_readme(en_chapters)
    validate(rows_by_chapter, zh_chapters, en_chapters)
    print(f"generated 120 chapters; English source chapters: {min(en_chapters)}-{max(en_chapters)}")


if __name__ == "__main__":
    main()
