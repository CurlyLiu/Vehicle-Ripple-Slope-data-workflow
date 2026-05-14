"""Tests for condition_mapper count helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.utils.condition_mapper import (
    REPORT_ITEMS,
    count_matched_images,
    count_matched_items,
    find_report_item_data,
)


def test_count_matched_items_all_empty():
    """All items have no matching records."""
    assert count_matched_items([]) == 0


def test_count_matched_items_all_matched():
    """All 9 items have matching records."""
    records = []
    for item in REPORT_ITEMS:
        for cond in item["conditions"]:
            records.append({
                "condition_name": cond["keywords"][0],
                "condition_id": cond["keywords"][0],
                "soc_level": "≥70%",
            })
    assert count_matched_items(records) == 9


def test_count_matched_items_partial():
    """Only some items match."""
    records = [
        {"condition_name": "静止低温", "condition_id": "静止低温", "soc_level": "≥70%"},
        {"condition_name": "零百加速", "condition_id": "零百加速", "soc_level": "≥70%"},
    ]
    assert count_matched_items(records) == 2


def test_count_matched_images_all_empty():
    """No images have matching records."""
    assert count_matched_images([]) == 0


def test_count_matched_images_partial():
    """Some images match."""
    records = [
        {"condition_name": "静止低温", "condition_id": "静止低温"},
        {"condition_name": "静止高温", "condition_id": "静止高温"},
        {"condition_name": "零百加速", "condition_id": "零百加速"},
    ]
    assert count_matched_images(records) == 3


def test_find_report_item_data_with_none_values():
    """Records exist but time_vpp is None should still return non-empty dict."""
    records = [
        {"condition_name": "静止低温", "condition_id": "静止低温", "time_vpp": None},
    ]
    matched = find_report_item_data(0, records)
    assert matched != {}
    assert matched["工况一"]["time_vpp"] is None
