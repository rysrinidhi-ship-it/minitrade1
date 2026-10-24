"""
Create / reset the database objects without needing the psql tool.

    python scripts/init_db.py            # schema + stocks/prices + demo trade history
    python scripts/init_db.py --clean    # schema + stocks/prices only (wallet stays Rs 1,00,000)

WARNING: schema.sql drops and recreates all tables.
"""
import argparse
import sys
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import Settings  # noqa: E402

DB_DIR = Path(__file__).resolve().parents[2] / "db"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--clean", action="store_true", help="skip the demo order history")
    args = parser.parse_args()

    files = ["schema.sql", "seed.sql"] + ([] if args.clean else ["seed_orders.sql"])
    conn = psycopg2.connect(Settings.from_env().database_url)
    conn.autocommit = True          # the .sql files contain their own BEGIN/COMMIT
    try:
        with conn.cursor() as cur:
            for name in files:
                print(f"running {name} ...")
                cur.execute((DB_DIR / name).read_text(encoding="utf-8"))
    finally:
        conn.close()
    print("done.")


if __name__ == "__main__":
    main()
