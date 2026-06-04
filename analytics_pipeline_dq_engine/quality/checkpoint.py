"""GE checkpoint: load bronze.raw_shipments → Z-score quality gate → exit 1 on failure."""

from __future__ import annotations

import os
import sys

import pandas as pd
from sqlalchemy import create_engine

from suite import validate_shipping_costs


def run_checkpoint(database_url: str) -> int:
    engine = create_engine(database_url, future=True)
    df = pd.read_sql_table("raw_shipments", con=engine, schema="bronze")

    result = validate_shipping_costs(df)
    s = result.statistics

    print("── Z-Score Quality Gate ──────────────────────────────────")
    print(f"  Rows:            {s.get('n_total', 0):>10,}")
    print(f"  Valid costs:     {s.get('n_valid', 0):>10,}")
    print(f"  Mean cost (USD): {s.get('mean', 0):>10,.2f}")
    print(f"  Std  cost (USD): {s.get('std', 0):>10,.2f}")
    print(f"  |Z| > 3 count:  {s.get('outlier_count', 0):>10,}")
    print(f"  Outlier ratio:   {s.get('outlier_ratio', 0):>10.4%}")
    print("──────────────────────────────────────────────────────────")

    if result.success:
        print("✓ PASS — all quality expectations met")
        return 0
    else:
        print("✗ FAIL — quality gate violations:")
        for d in result.details:
            print(f"   • {d}")
        return 1


if __name__ == "__main__":
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://analytics:analytics@localhost:5432/analytics",
    )
    sys.exit(run_checkpoint(db_url))
