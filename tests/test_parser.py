import pytest
from src.parser import parse_date, parse_nav_file, parse_scheme_meta


def test_parse_date():
    assert parse_date("29-Jun-2026") == "2026-06-29"
    assert parse_date("2026-06-30") == "2026-06-30"
    with pytest.raises(ValueError):
        parse_date("invalid-date-string")


def test_parse_scheme_meta():
    meta = parse_scheme_meta("data/scheme_meta.csv")
    assert len(meta) > 0
    assert 100104 in meta
    assert meta[100104]["amc_name"] == "Aditya Birla Sun Life MF"


def test_parse_nav_file():
    records, exclusions = parse_nav_file("data/nav_2026-06-29.txt")
    assert len(records) > 0
    # Check that invalid N.A. values were recorded in exclusions
    assert 100137 in exclusions
    assert "N.A." in exclusions[100137]
