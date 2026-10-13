"""Build the canonical NZ vehicle table from the NZTA Motor Vehicle Register.

Input: the register as downloaded from NZTA (CC-BY 4.0), in data/mvr/ —
either the all-years .zip, the per-year .csv files, or both.

    curl -L -o data/mvr/Fleet-data-all-vehicle-years.zip \
      https://wksprdgisopendata.blob.core.windows.net/motorvehicleregister/Fleet-data-all-vehicle-years.zip

DuckDB reads .csv, .csv.gz and .csv.zst but NOT .zip, so a zip is expanded
first — to .csv.gz, which is a third of the disk of a plain .csv and which
DuckDB reads directly. The expansion happens once; later runs reuse it.

Output: nz_vehicle_resolver/data/mvr_canonical_vehicles.csv — one row per distinct MAKE|MODEL with
fleet count, used-import count and vehicle-year range. Aggregation is in SQL;
5.8M rows never enter Python.

MIN_FLEET is the only judgement here. Pairs below it are the register's own
free-text noise — NZTA documents that its free-text fields carry "spelling
mistakes and inconsistent wording" surviving their algorithmic cleaning. The
script prints the coverage the cut achieves, so the number is reportable
rather than assumed. Pass 1 to keep everything.

Usage: python3 build_canonical.py [min_fleet]
"""

import glob
import gzip
import os
import shutil
import sys
import zipfile

import duckdb

SRC_DIR = "data/mvr"
OUT = "nz_vehicle_resolver/data/mvr_canonical_vehicles.csv"
MIN_FLEET = 10


def expand_zips():
    """Turn any .zip into sibling .csv.gz files DuckDB can read. Idempotent."""
    for zpath in sorted(glob.glob(os.path.join(SRC_DIR, "*.zip"))):
        with zipfile.ZipFile(zpath) as z:
            for entry in z.infolist():
                if entry.is_dir() or not entry.filename.lower().endswith(".csv"):
                    continue
                out = os.path.join(SRC_DIR, os.path.basename(entry.filename) + ".gz")
                if os.path.exists(out):
                    print(f"  reusing {out}")
                    continue
                print(
                    f"  expanding {entry.filename} "
                    f"({entry.file_size/1e9:.2f}GB) -> {out}"
                )
                with z.open(entry) as src, gzip.open(out, "wb", compresslevel=1) as dst:
                    shutil.copyfileobj(src, dst, length=8 << 20)


def main():
    min_fleet = int(sys.argv[1]) if len(sys.argv) > 1 else MIN_FLEET

    if not os.path.isdir(SRC_DIR):
        sys.exit(f"{SRC_DIR}/ does not exist — see the README for the download.")
    expand_zips()

    files = sorted(
        glob.glob(os.path.join(SRC_DIR, "*.csv"))
        + glob.glob(os.path.join(SRC_DIR, "*.csv.gz"))
    )
    if not files:
        sys.exit(
            f"No register CSVs in {SRC_DIR}/. Download from NZTA (CC-BY 4.0):\n"
            "  https://www.nzta.govt.nz/resources/new-zealand-motor-vehicle-register"
            "-statistics/new-zealand-vehicle-fleet-open-data-sets/"
        )
    print(f"reading {len(files)} file(s):")
    for f in files:
        print(f"  {f}  ({os.path.getsize(f)/1e6:.0f}MB)")

    # File list is inlined, not bound: read_csv() takes a list literal, and a
    # bound parameter arrives as a single value it tries to sniff as a path.
    src = "[" + ", ".join("'" + f.replace("'", "''") + "'" for f in files) + "]"

    con = duckdb.connect()
    con.execute("SET preserve_insertion_order=false")
    print("aggregating…")
    con.execute(
        f"""
        CREATE TABLE canon AS
        SELECT
            UPPER(TRIM(MAKE))  AS make,
            UPPER(TRIM(MODEL)) AS model,
            CAST(COUNT(*) AS INTEGER) AS fleet_count,
            CAST(SUM(CASE WHEN UPPER(TRIM(COALESCE(IMPORT_STATUS,''))) = 'NEW'
                          THEN 0 ELSE 1 END) AS INTEGER) AS used_import_count,
            MIN(TRY_CAST(VEHICLE_YEAR AS INTEGER)) AS min_vehicle_year,
            MAX(TRY_CAST(VEHICLE_YEAR AS INTEGER)) AS max_vehicle_year
        FROM read_csv({src}, union_by_name=true, all_varchar=true)
        WHERE MAKE IS NOT NULL AND TRIM(MAKE) <> ''
          AND MODEL IS NOT NULL AND TRIM(MODEL) <> ''
        GROUP BY 1, 2
        """
    )

    pairs, total = con.execute(
        "SELECT COUNT(*), SUM(fleet_count) FROM canon"
    ).fetchone()
    print(f"  {total:,} rows, {pairs:,} distinct make/model pairs")

    print("  coverage by cut:")
    for t in (1, 3, 5, 10, 25, 100):
        k, c = con.execute(
            "SELECT COUNT(*), SUM(fleet_count) FROM canon WHERE fleet_count >= ?", [t]
        ).fetchone()
        mark = "  <- using" if t == min_fleet else ""
        print(f"    n>={t:<4} {k:>7,} pairs  {100*c/total:6.2f}% of fleet{mark}")

    con.execute(
        f"COPY (SELECT make, model, fleet_count, used_import_count, "
        f"min_vehicle_year, max_vehicle_year FROM canon "
        f"WHERE fleet_count >= {min_fleet} ORDER BY fleet_count DESC) "
        f"TO '{OUT}' (HEADER, DELIMITER ',')"
    )
    print(f"wrote {OUT}")

    print("\ntop 12 by fleet:")
    for r in con.execute(
        "SELECT make, model, fleet_count, used_import_count FROM canon "
        "ORDER BY fleet_count DESC LIMIT 12"
    ).fetchall():
        pct = 100 * r[3] / r[2]
        print(f"  {r[0]:<12} {r[1]:<16} fleet={r[2]:<8} used_import={pct:5.1f}%")


if __name__ == "__main__":
    main()
