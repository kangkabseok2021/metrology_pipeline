"""Generate deliberately messy supply-chain shipment data for ELT testing.

Injects 5 quality issues into the output CSV so every cleaning step in the
dbt staging model is exercised by real data.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

HUBS = [
    "NYC", "LAX", "CHI", "HOU", "PHX", "PHI", "SAN", "DAL", "SJC", "AUS",
    "LHR", "CDG", "FRA", "AMS", "MAD", "BCN", "MXP", "ZRH", "VIE", "BRU",
]
SKUS = [f"SKU-{i:03d}" for i in range(1, 21)]
CARRIERS = ["FedEx", "UPS", "DHL", "USPS", "TNT", "Maersk"]
REGIONS = {
    "NYC": ("Northeast", "USA"), "LAX": ("West", "USA"),
    "CHI": ("Midwest", "USA"), "HOU": ("South", "USA"),
    "PHX": ("Southwest", "USA"), "PHI": ("Northeast", "USA"),
    "SAN": ("West", "USA"), "DAL": ("South", "USA"),
    "SJC": ("West", "USA"), "AUS": ("South", "USA"),
    "LHR": ("North", "GBR"), "CDG": ("West", "FRA"),
    "FRA": ("West", "DEU"), "AMS": ("West", "NLD"),
    "MAD": ("South", "ESP"), "BCN": ("South", "ESP"),
    "MXP": ("North", "ITA"), "ZRH": ("Central", "CHE"),
    "VIE": ("East", "AUT"), "BRU": ("West", "BEL"),
}


def generate_raw_data(n_rows: int = 25_000, seed: int = 42) -> pd.DataFrame:
    """Return a DataFrame with realistic supply-chain data + injected issues."""
    rng = np.random.default_rng(seed)
    date_range = pd.date_range("2022-01-01", "2023-06-30", freq="D")

    hubs_origin = rng.choice(HUBS, size=n_rows)
    hubs_dest = rng.choice(HUBS, size=n_rows)
    same_mask = hubs_origin == hubs_dest
    hubs_dest[same_mask] = np.roll(HUBS, 1)[
        np.searchsorted(HUBS, hubs_origin[same_mask])
    ]

    df = pd.DataFrame({
        "shipment_id":       [f"SHP-{i:07d}" for i in range(n_rows)],
        "origin_hub":        hubs_origin,
        "destination_hub":   hubs_dest,
        "product_sku":       rng.choice(SKUS, size=n_rows),
        "carrier":           rng.choice(CARRIERS, size=n_rows),
        "ship_date":         rng.choice(date_range, size=n_rows).astype(str),
        "weight_kg":         rng.uniform(0.5, 100.0, size=n_rows).round(2),
        "quantity":          rng.integers(1, 500, size=n_rows),
        "shipping_cost_usd": rng.uniform(10.0, 5_000.0, size=n_rows).round(2),
    })

    # ── Inject quality issues ─────────────────────────────────────────────────
    # 1. 5% null shipping_cost_usd
    null_idx = rng.choice(n_rows, size=int(n_rows * 0.05), replace=False)
    df.loc[null_idx, "shipping_cost_usd"] = None

    # 2. 2% negative costs (invalid)
    neg_idx = rng.choice(n_rows, size=int(n_rows * 0.02), replace=False)
    df.loc[neg_idx, "shipping_cost_usd"] = -rng.uniform(1.0, 500.0, size=len(neg_idx)).round(2)

    # 3. 3% duplicate rows appended then shuffled
    dup_idx = rng.choice(n_rows, size=int(n_rows * 0.03), replace=False)
    dupes = df.iloc[dup_idx].copy()
    df = pd.concat([df, dupes], ignore_index=True).sample(frac=1, random_state=seed)

    # 4. 1% whitespace-padded hub codes (e.g. ' NYC ')
    pad_idx = rng.choice(len(df), size=int(len(df) * 0.01), replace=False)
    df.loc[pad_idx, "origin_hub"] = " " + df.loc[pad_idx, "origin_hub"] + " "

    # 5. 0.5% dates in MM/DD/YYYY instead of YYYY-MM-DD
    fmt_idx = rng.choice(len(df), size=int(len(df) * 0.005), replace=False)
    df.loc[fmt_idx, "ship_date"] = pd.to_datetime(
        df.loc[fmt_idx, "ship_date"]
    ).dt.strftime("%m/%d/%Y")

    return df.reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate raw shipment CSV")
    ap.add_argument("--rows",   type=int, default=25_000)
    ap.add_argument("--output", type=Path, default=Path("/tmp/raw_shipments.csv"))
    ap.add_argument("--seed",   type=int, default=42)
    args = ap.parse_args()

    df = generate_raw_data(n_rows=args.rows, seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)
    print(f"Generated {len(df):,} rows → {args.output}")


if __name__ == "__main__":
    main()
