import csv
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional


def parse_scheme_meta(csv_path: str) -> Dict[int, Dict[str, str]]:
    """
    Parses scheme_meta.csv into a dictionary keyed by amfi_code.
    """
    metadata: Dict[int, Dict[str, str]] = {}
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                amfi_code = int(row["amfi_code"].strip())
                metadata[amfi_code] = {
                    "amc_name": row["amc_name"].strip(),
                    "sebi_category": row["sebi_category"].strip(),
                    "plan": row["plan"].strip(),
                    "option": row["option"].strip(),
                }
            except (ValueError, KeyError):
                continue
    return metadata


def parse_date(date_str: str) -> str:
    """
    Normalizes date string to YYYY-MM-DD format.
    Supports formats like '29-Jun-2026' and '2026-06-29'.
    """
    date_str = date_str.strip()
    for fmt in ("%d-%b-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    raise ValueError(f"Unrecognized date format: '{date_str}'")


def parse_nav_file(file_path: str) -> Tuple[List[Dict[str, Any]], Dict[int, str]]:
    """
    Parses an AMFI text file.
    Returns:
      - valid_records: List of parsed scheme records
      - file_exclusions: Mapping of amfi_code -> exclusion reason for issues discovered in this file
    """
    records: List[Dict[str, Any]] = []
    file_exclusions: Dict[int, str] = {}
    
    current_amc: Optional[str] = None
    current_category: Optional[str] = None
    
    seen_codes_in_file: Dict[int, Dict[str, Any]] = {}
    
    with open(file_path, mode="r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            
            # Header row check
            if line.startswith("Scheme Code;"):
                continue
            
            # Category header check
            if any(line.startswith(prefix) for prefix in ("Open Ended Schemes", "Close Ended Schemes", "Interval Schemes")):
                current_category = line
                continue
            
            # Semicolon separated row check
            if ";" in line:
                parts = [p.strip() for p in line.split(";")]
                if len(parts) < 6:
                    continue
                
                raw_code, isin1, isin2, scheme_name, raw_nav, raw_date = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
                
                try:
                    amfi_code = int(raw_code)
                except ValueError:
                    continue
                
                try:
                    norm_date = parse_date(raw_date)
                except ValueError:
                    file_exclusions[amfi_code] = f"Invalid date format '{raw_date}' in file"
                    continue
                
                # Check for duplicate scheme records within the same day's file
                if amfi_code in seen_codes_in_file:
                    existing = seen_codes_in_file[amfi_code]
                    if existing["raw_nav"] != raw_nav:
                        file_exclusions[amfi_code] = f"Duplicate conflicting NAV records on {norm_date}"
                    continue
                
                # Validate NAV value
                is_valid = True
                nav_float = None
                error_reason = None
                
                if raw_nav.upper() == "N.A." or not raw_nav:
                    is_valid = False
                    error_reason = "NAV value is N.A. or missing"
                    file_exclusions[amfi_code] = f"NAV value is N.A. on {norm_date}"
                else:
                    try:
                        nav_float = float(raw_nav)
                        if nav_float <= 0:
                            is_valid = False
                            error_reason = "Non-positive NAV value"
                            file_exclusions[amfi_code] = f"Non-positive NAV value ({nav_float}) on {norm_date}"
                    except ValueError:
                        is_valid = False
                        error_reason = f"Non-numeric NAV value '{raw_nav}'"
                        file_exclusions[amfi_code] = f"Non-numeric NAV value '{raw_nav}' on {norm_date}"
                
                record = {
                    "amfi_code": amfi_code,
                    "isin_payout_growth": isin1 if isin1 != "-" else None,
                    "isin_reinvestment": isin2 if isin2 != "-" else None,
                    "scheme_name": scheme_name,
                    "nav": nav_float,
                    "raw_nav": raw_nav,
                    "nav_date": norm_date,
                    "amc_name": current_amc,
                    "sebi_category": current_category,
                    "is_valid": is_valid,
                    "error_reason": error_reason,
                }
                
                seen_codes_in_file[amfi_code] = record
                if is_valid:
                    records.append(record)
            else:
                # AMC Section Header
                current_amc = line
                
    return records, file_exclusions
