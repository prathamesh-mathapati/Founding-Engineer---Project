import json
import jsonschema
from src.report import generate_report


def test_generate_report_schema_valid():
    d1_records = [
        {
            "amfi_code": 100001,
            "nav_date": "2026-06-29",
            "nav": 100.0,
            "raw_nav": "100.0000",
            "scheme_name": "Test Scheme 1",
            "amc_name": "Test Mutual Fund",
            "is_valid": True,
            "error_reason": None,
        },
        {
            "amfi_code": 100002,
            "nav_date": "2026-06-29",
            "nav": 50.0,
            "raw_nav": "50.0000",
            "scheme_name": "Test Scheme 2",
            "amc_name": "Test Mutual Fund",
            "is_valid": True,
            "error_reason": None,
        },
        {
            "amfi_code": 100003,
            "nav_date": "2026-06-29",
            "nav": 200.0,
            "raw_nav": "200.0000",
            "scheme_name": "Test Scheme 3",
            "amc_name": "Test Mutual Fund",
            "is_valid": True,
            "error_reason": None,
        },
    ]

    d2_records = [
        {
            "amfi_code": 100001,
            "nav_date": "2026-06-30",
            "nav": 101.0,
            "raw_nav": "101.0000",
            "scheme_name": "Test Scheme 1",
            "amc_name": "Test Mutual Fund",
            "is_valid": True,
            "error_reason": None,
        },
        {
            "amfi_code": 100002,
            "nav_date": "2026-06-30",
            "nav": 49.5,
            "raw_nav": "49.5000",
            "scheme_name": "Test Scheme 2",
            "amc_name": "Test Mutual Fund",
            "is_valid": True,
            "error_reason": None,
        },
        {
            "amfi_code": 100003,
            "nav_date": "2026-06-30",
            "nav": 200.6,
            "raw_nav": "200.6000",
            "scheme_name": "Test Scheme 3",
            "amc_name": "Test Mutual Fund",
            "is_valid": True,
            "error_reason": None,
        },
    ]

    report = generate_report(
        d1_records=d1_records,
        d2_records=d2_records,
        file_exclusions={},
        schema_path="output_schema.json"
    )

    assert report["schemes_loaded"] == 3
    assert report["schemes_excluded"] == 0
    assert len(report["by_amc"]) == 1
    assert report["by_amc"][0]["amc"] == "Test Mutual Fund"
    # Worked example median check: changes are +1.0%, -1.0%, +0.3% -> Median is 0.3
    assert report["by_amc"][0]["median_1d_change_pct"] == 0.3

    with open("output_schema.json") as f:
        schema = json.load(f)
    jsonschema.validate(instance=report, schema=schema)
