import json
import statistics
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
import jsonschema


def generate_report(
    d1_records: List[Dict[str, Any]],
    d2_records: List[Dict[str, Any]],
    file_exclusions: Dict[int, str],
    schema_path: str = "output_schema.json"
) -> Dict[str, Any]:
    """
    Computes AMC statistics and builds report.json according to output_schema.json.
    """
    # 1. Identify distinct dates
    dates_set = set()
    for r in d1_records + d2_records:
        dates_set.add(r["nav_date"])
    source_dates = sorted(list(dates_set))
    
    if len(source_dates) < 2:
        raise ValueError(f"Expected at least 2 distinct source dates, got {source_dates}")
        
    date1, date2 = source_dates[0], source_dates[1]
    
    # Map valid records by amfi_code for each date
    map_d1: Dict[int, Dict[str, Any]] = {r["amfi_code"]: r for r in d1_records if r["is_valid"]}
    map_d2: Dict[int, Dict[str, Any]] = {r["amfi_code"]: r for r in d2_records if r["is_valid"]}
    
    all_codes = set(map_d1.keys()).union(set(map_d2.keys()))
    all_codes.update(file_exclusions.keys())
    
    exclusions_dict: Dict[int, str] = dict(file_exclusions)
    included_schemes: Dict[int, Dict[str, Any]] = {}
    amc_changes: Dict[str, List[float]] = {}
    
    for code in sorted(list(all_codes)):
        if code in exclusions_dict:
            continue
            
        r1 = map_d1.get(code)
        r2 = map_d2.get(code)
        
        if not r1:
            exclusions_dict[code] = f"Scheme missing on day 1 ({date1})"
            continue
        if not r2:
            exclusions_dict[code] = f"Scheme missing on day 2 ({date2})"
            continue
            
        nav1 = r1.get("nav")
        nav2 = r2.get("nav")
        
        if nav1 is None or nav1 <= 0:
            exclusions_dict[code] = f"Invalid NAV on {date1}"
            continue
        if nav2 is None or nav2 <= 0:
            exclusions_dict[code] = f"Invalid NAV on {date2}"
            continue
            
        # Calculate 1-day percentage change
        change_pct = ((nav2 - nav1) / nav1) * 100.0
        
        # Use AMC name as it appears in the NAV file header
        amc_name = r1.get("amc_name") or r2.get("amc_name") or "Unknown AMC"
        
        if amc_name not in amc_changes:
            amc_changes[amc_name] = []
        amc_changes[amc_name].append(change_pct)
        
        included_schemes[code] = {
            "amc": amc_name,
            "nav_d1": nav1,
            "nav_d2": nav2,
            "change_pct": change_pct
        }
        
    # Build exclusions array sorted by amfi_code ascending
    exclusions_list = [
        {"amfi_code": int(code), "reason": str(reason)}
        for code, reason in sorted(exclusions_dict.items(), key=lambda x: x[0])
    ]
    
    # Build by_amc array sorted by amc name ascending
    by_amc_list = []
    for amc_name in sorted(amc_changes.keys()):
        changes = amc_changes[amc_name]
        scheme_count = len(changes)
        if scheme_count > 0:
            med_val = statistics.median(changes)
            med_rounded = round(float(med_val), 4)
        else:
            med_rounded = None
            
        by_amc_list.append({
            "amc": amc_name,
            "scheme_count": scheme_count,
            "median_1d_change_pct": med_rounded
        })
        
    # UTC timestamp with trailing 'Z'
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    report = {
        "generated_at": now_utc,
        "source_dates": source_dates,
        "schemes_loaded": len(included_schemes),
        "schemes_excluded": len(exclusions_list),
        "exclusions": exclusions_list,
        "by_amc": by_amc_list
    }
    
    # Validate against output_schema.json
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    jsonschema.validate(instance=report, schema=schema)
    
    return report
