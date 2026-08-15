from __future__ import annotations

import importlib.util
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD_PATH = ROOT / "scripts" / "build.py"

spec = importlib.util.spec_from_file_location("dream_build", BUILD_PATH)
assert spec and spec.loader
dream_build = importlib.util.module_from_spec(spec)
sys.modules["dream_build"] = dream_build
spec.loader.exec_module(dream_build)


def load_rows() -> list[dict]:
    return [json.loads(line) for line in (ROOT / "data" / "alignment.jsonl").read_text(encoding="utf-8").splitlines()]


def rows_by_chapter() -> dict[int, list[dict]]:
    by_chapter: dict[int, list[dict]] = defaultdict(list)
    for row in load_rows():
        by_chapter[row["chapter"]].append(row)
    return dict(by_chapter)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text)


def english_window(rows: list[dict], index: int, distance: int = 3) -> str:
    start = max(0, index - distance)
    end = min(len(rows), index + distance + 1)
    return " ".join(row["en"] for row in rows[start:end])


def english_near_zh(chapter: int, zh: str, en: str, distance: int = 3) -> bool:
    rows = rows_by_chapter()[chapter]
    for index, row in enumerate(rows):
        if zh in row["zh"] and en.casefold() in english_window(rows, index, distance).casefold():
            return True
    return False


def test_all_chapters_exist_and_have_sequential_verses() -> None:
    chapters = rows_by_chapter()
    assert set(chapters) == set(range(1, 121))
    for chapter, rows in chapters.items():
        assert rows
        assert [row["verse"] for row in rows] == list(range(1, len(rows) + 1))
        assert all(row["zh"].strip() for row in rows)


def test_source_segments_are_preserved() -> None:
    chapters = rows_by_chapter()
    zh_sources = dream_build.read_zh_chapters()
    en_sources = dream_build.read_en_chapters()
    for chapter in range(1, 121):
        expected_zh = "".join(segment.text for segment in dream_build.split_zh(zh_sources[chapter]))
        actual_zh = "".join(row["zh"] for row in chapters[chapter])
        assert normalize_text(actual_zh) == normalize_text(expected_zh)

        if chapter in en_sources:
            expected_en = " ".join(segment.text for segment in dream_build.split_en(en_sources[chapter]))
            actual_en = " ".join(row["en"] for row in chapters[chapter] if row["en"])
            assert normalize_text(actual_en) == normalize_text(expected_en)


def test_source_offsets_are_monotonic() -> None:
    for chapter, rows in rows_by_chapter().items():
        previous_zh_end = 0
        previous_en_end = 0
        for row in rows:
            assert row["zh_start"] >= previous_zh_end
            assert row["zh_end"] >= row["zh_start"]
            previous_zh_end = row["zh_end"]
            if row["en_start"] is not None:
                assert row["en_start"] >= previous_en_end
                assert row["en_end"] >= row["en_start"]
                previous_en_end = row["en_end"]


def test_chinese_verses_are_sentence_sized() -> None:
    rows = load_rows()
    full_stop_counts = [row["zh"].count("。") for row in rows]
    at_most_one = sum(count <= 1 for count in full_stop_counts) / len(full_stop_counts)
    three_or_more = sum(count >= 3 for count in full_stop_counts) / len(full_stop_counts)
    assert at_most_one > 0.98
    assert three_or_more == 0
    assert max(len(row["zh"]) for row in rows) < 320


def test_chinese_sentence_punctuation_is_preserved() -> None:
    punctuated = [row for row in load_rows() if row["zh"].endswith(("。", "！", "？", "。”", "！”", "？”"))]
    assert len(punctuated) > 25000
    assert any(row["zh"].endswith("！") or row["zh"].endswith("！”") for row in load_rows())
    assert any(row["zh"].endswith("？") or row["zh"].endswith("？”") for row in load_rows())


def test_compact_verse_headings_are_generated() -> None:
    master = (ROOT / "master.tex").read_text(encoding="utf-8")
    assert r"\Book{石頭記}{1}{80}" in master
    assert r"\Book{後四十回}{81}{120}" in master
    assert "Book I -- Shi Tou Ji" not in master
    assert "Book II -- Later Continuation" not in master


def test_bilingual_regression_anchors() -> None:
    anchors = [
        (1, "甄士隐", "Chen Shih-yin"),
        (1, "女娲", "Nü Wo"),
        (1, "青埂峰", "Ch'ing Keng"),
        (1, "贾雨村", "Yü-ts"),
        (3, "王熙凤", "Hsi-feng"),
        (3, "宝玉来了", "Pao-yü was coming"),
        (4, "葫芦庙", "Hu Lu temple"),
        (4, "薛蟠", "Hsüeh P"),
        (5, "太虚幻境", "Great Void"),
        (5, "宝玉", "Pao-yü"),
        (6, "刘老老", "goody Liu"),
        (6, "凤姐", "lady Feng"),
        (10, "秦钟", "Ch'in Chung"),
        (10, "张先生", "Chang"),
        (20, "耗子精", "rat"),
        (20, "袭人", "Hsi Jen"),
        (40, "鸳鸯", "Yüan Yang"),
        (40, "刘老老", "goody Liu"),
        (50, "宝琴", "Pao-ch"),
        (50, "湘云", "Hsiang-yün"),
        (56, "宝钗", "Pao-ch"),
    ]
    for chapter, zh, en in anchors:
        assert english_near_zh(chapter, zh, en), (chapter, zh, en)


def test_chapter_boundary_anchors() -> None:
    chapters = rows_by_chapter()
    opening_anchors = {
        1: "――此开卷第一回也。",
        2: "却说封肃听见公差传唤",
        5: "第四回中既将薛家母子",
        40: "话说宝玉听了",
        80: "话说金桂听了",
        81: "且说迎春归去之后",
        100: "话说贾政去见节度",
        119: "话说莺儿见宝玉说话",
        120: "话说宝钗听秋纹说袭人不好",
    }
    for chapter, anchor in opening_anchors.items():
        first_text = "".join(row["zh"] for row in chapters[chapter][:3])
        assert anchor in first_text

    closing_anchors = {
        80: "要知后事，下回分解。",
        120: "说到辛酸处，荒唐愈可悲。",
    }
    for chapter, anchor in closing_anchors.items():
        last_text = "".join(row["zh"] for row in chapters[chapter][-8:])
        assert anchor in last_text
