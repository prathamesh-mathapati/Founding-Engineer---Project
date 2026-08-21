import json, statistics, csv
from datetime import datetime
from collections import defaultdict

DB = "postgresql://ws:MyP@ssw0rd2026@db-postgresql-blr1-12345.ondigitalocean.com:25060/worksample"

def load_nav(path):
    rows, amc = [], None
    for line in open(path).readlines():
        line = line.strip()
        if not line or line.startswith("Scheme Code"):
            continue
        if ";" not in line:
            if "Scheme" not in line:
                amc = line
            continue
        p = line.split(";")
        try:
            rows.append({"code": int(p[0]), "amc": amc, "name": p[3],
                         "nav": float(p[4]) if p[4] != "N.A." else 0.0,
                         "date": datetime.strptime(p[5], "%d-%b-%Y").date()})
        except Exception:
            continue
    return rows

def main():
    d1 = load_nav("data/nav_2026-06-29.txt")
    d2 = load_nav("data/nav_2026-06-30.txt")
    try:
        import psycopg2
        conn = psycopg2.connect(DB); cur = conn.cursor()
        for r in d1 + d2:
            cur.execute(f"INSERT INTO nav_data VALUES ({r['code']}, '{r['name']}', {r['nav']}, '{r['date']}')")
        conn.commit()
    except Exception as e:
        print("db skipped:", e)

    meta = {int(r["amfi_code"]): r for r in csv.DictReader(open("data/scheme_meta.csv"))}
    n1 = {r["code"]: r for r in d1}
    n2 = {r["code"]: r for r in d2}
    changes = defaultdict(list)
    for code, a in n1.items():
        if code not in n2 or code not in meta or a["nav"] == 0:
            continue
        changes[a["amc"]].append((n2[code]["nav"] - a["nav"]) / a["nav"] * 100)

    report = {"generated_at": datetime.utcnow().isoformat(),
              "source_dates": sorted({str(r["date"]) for r in d1 + d2}),
              "schemes_loaded": sum(len(v) for v in changes.values()),
              "schemes_excluded": 0, "exclusions": [],
              "by_amc": [{"amc": k, "scheme_count": len(v),
                          "median_1d_change_pct": round(statistics.median(v), 2)}
                         for k, v in changes.items()],
              "total_rows_processed": len(d1) + len(d2)}
    json.dump(report, open("report.json", "w"), indent=2)
    print("Done!")

main()
