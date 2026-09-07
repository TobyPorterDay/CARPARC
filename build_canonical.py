"""Build the canonical NZ vehicle table from the NZTA Motor Vehicle Register.

Input: the register's CSVs, as downloaded from NZTA (CC-BY 4.0). Either
  - data/mvr/Fleet-data-all-vehicle-years.zip   (one 309MB zip, all years), or
  - data/mvr/VehicleYear-*.csv                  (per-year files)
Put either under data/mvr/ and run this.

Output: data/mvr_canonical_vehicles.csv -- one row per distinct MAKE|MODEL,
with fleet count, used-import count and the vehicle-year range. Aggregation is
done in DuckDB (SQL), which reads the CSVs and the zip directly and never
holds 5.8M rows in Python.

MIN_FLEET is the only judgement in here: pairs below it are free-text noise in
the register's own words ("spelling mistakes and inconsistent wording"). The
script prints the coverage the cut achieves so the number is reportable rather
than assumed. Lower it to 1 to keep everything.

Usage: python3 build_canonical.py [min_fleet]
"""

import glob
import os
import sys

import duckdb

SRC_DIR = "data/mvr"
OUT = "data/mvr_canonical_vehicles.csv"
MIN_FLEET = 10


def sources():
    csvs = sorted(glob.glob(os.path.join(SRC_DIR, "VehicleYear*.csv")))
    zips = sorted(glob.glob(os.path.join(SRC_DIR, "*.zip")))
    if csvs:
        return csvs, f"{len(csvs)} per-year CSVs"
    if zips:
        return zips, f"{len(zips)} zip archive(s)"
    sys.exit(
        f"No register files in {SRC_DIR}/.\n"
        "Download from NZTA (CC-BY 4.0) and put them there:\n"
        "  https://www.nzta.govt.nz/resources/new-zealand-motor-vehicle-register-statistics"
        "/new-zealand-vehicle-fleet-open-data-sets/"
    )


def main():
    min_fleet = int(sys.argv[1]) if len(sys.argv) > 1 else MIN_FLEET
    files, what = sources()
    print(f"reading {what} from {SRC_DIR}/")

    con = duckdb.connect()
    con.execute("SET preserve_insertion_order=false")
    con.execute(
        """
        CREATE TABLE mvr AS
        SELECT
            UPPER(TRIM(MAKE))  AS make,
            UPPER(TRIM(MODEL)) AS model,
            CASE WHEN UPPER(TRIM(COALESCE(IMPORT_STATUS,''))) = 'NEW'
                 THEN 0 ELSE 1 END AS is_used_import,
            TRY_CAST(VEHICLE_YEAR AS INTEGER) AS vehicle_year
        FROM read_csv_auto(?, union_by_name=true, ignore_errors=true)
        WHERE MAKE IS NOT NULL AND MODEL IS NOT NULL
          AND TRIM(MAKE) <> '' AND TRIM(MODEL) <> ''
        """,
        [files],
    )

    total = con.execute("SELECT COUNT(*) FROM mvr").fetchone()[0]
    distinct = con.execute("SELECT COUNT(*) FROM (SELECT DISTINCT make, model FROM mvr)").fetchone()[0]
    print(f"  {total:,} rows, {distinct:,} distinct make/model pairs")

    con.execute(
        """
        CREATE TABLE canon AS
        SELECT make, model,
               CAST(COUNT(*) AS INTEGER)              AS fleet_count,
               CAST(SUM(is_used_import) AS INTEGER)   AS used_import_count,
               MIN(vehicle_year)                      AS min_vehicle_year,
               MAX(vehicle_year)                      AS max_vehicle_year
        FROM mvr GROUP BY make, model
        """
    )

    kept, covered = con.execute(
        "SELECT COUNT(*), SUM(fleet_count) FROM canon WHERE fleet_count >= ?",
        [min_fleet],
    ).fetchone()
    print(
        f"  cut at fleet_count >= {min_fleet}: {kept:,} pairs, "
        f"{covered:,} vehicles = {100*covered/total:.2f}% of the fleet"
    )

    con.execute(
        f"COPY (SELECT make, model, fleet_count, used_import_count, "
        f"min_vehicle_year, max_vehicle_year FROM canon "
        f"WHERE fleet_count >= {min_fleet} ORDER BY fleet_count DESC) "
        f"TO '{OUT}' (HEADER, DELIMITER ',')"
    )
    print(f"wrote {OUT}")
    print("\ntop 10:")
    for r in con.execute(
        "SELECT make, model, fleet_count, used_import_count FROM canon "
        "ORDER BY fleet_count DESC LIMIT 10"
    ).fetchall():
        print(f"  {r[0]:<12} {r[1]:<16} fleet={r[2]:<8} used_import={r[3]}")


if __name__ == "__main__":
    main()
