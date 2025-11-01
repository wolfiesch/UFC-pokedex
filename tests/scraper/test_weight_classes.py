from __future__ import annotations

from scraper.utils.weight_classes import parse_weight_lbs, weight_to_division


def test_parse_weight_lbs_extracts_numeric_value():
    assert parse_weight_lbs("155 lbs.") == 155.0
    assert parse_weight_lbs("205 LBS") == 205.0


def test_parse_weight_lbs_handles_invalid_input():
    assert parse_weight_lbs("not available") is None
    assert parse_weight_lbs(None) is None


def test_weight_to_division_maps_known_ranges():
    assert weight_to_division("155 lbs.") == "Lightweight"
    assert weight_to_division("170") == "Welterweight"
    assert weight_to_division("0 lbs.") is None
    assert weight_to_division(None) is None


def test_weight_to_division_handles_heavyweights():
    assert weight_to_division("265 lbs.") == "Heavyweight"
    assert weight_to_division("280 lbs.") == "Super Heavyweight"
