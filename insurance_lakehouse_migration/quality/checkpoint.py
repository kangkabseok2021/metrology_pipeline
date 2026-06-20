"""Gold quality checkpoint: load Gold Delta tables → convert to pandas → run suite."""

from __future__ import annotations

import os
import sys


def run_checkpoint(gold_path: str | None = None) -> int:
    from pipeline.spark_session import get_spark
    from quality.suite import validate_gold_tables

    path = gold_path or os.environ.get("GOLD_PATH", "./data/gold")
    spark = get_spark("insurance_quality_checkpoint")

    fact_claims = spark.read.format("delta").load(f"{path}/fact_claims").toPandas()
    fact_premiums = spark.read.format("delta").load(f"{path}/fact_premiums").toPandas()
    dim_policy = spark.read.format("delta").load(f"{path}/dim_policy").toPandas()

    result = validate_gold_tables(fact_claims, fact_premiums, dim_policy)

    print("── Gold Quality Gate ─────────────────────────────────────")
    print(f"  fact_claims rows : {result.statistics.get('fact_claims_rows', 0):>8,}")
    print(f"  fact_premiums    : {result.statistics.get('fact_premiums_rows', 0):>8,}")
    print(f"  payout outliers  : {result.statistics.get('payout_outlier_count', 0):>8,}")
    print(f"  outlier ratio    : {result.statistics.get('payout_outlier_ratio', 0):>8.4%}")
    print("──────────────────────────────────────────────────────────")

    if result.success:
        print("✓ PASS — all Gold quality expectations met")
        return 0
    else:
        print("✗ FAIL — quality gate violations:")
        for d in result.details:
            print(f"   • {d}")
        return 1


if __name__ == "__main__":
    sys.exit(run_checkpoint())
