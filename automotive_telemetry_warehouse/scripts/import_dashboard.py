"""Import the Fleet Telemetry dashboard bundle into Superset via the REST API.

The CLI (`superset import-dashboards`) cannot supply a password for the
read-only Postgres connection a v1 dashboard bundle declares, so it always
fails on a fresh instance with `sqlalchemy_uri` containing `XXXXXXXXXX`.
`POST /api/v1/dashboard/import/` accepts a `passwords` map keyed by the
database YAML's path inside the bundle, which is the only import path that
can provision the connection correctly.

Zips `superset/dashboards/bundle/` on the fly, wrapping it in a root directory
(Superset's importer strips the first path component of every bundle member,
mirroring the structure `superset export-dashboards` produces).
"""

from __future__ import annotations

import argparse
import io
import json
import os
import zipfile
from pathlib import Path

import httpx

BUNDLE_DIR = Path(__file__).resolve().parent.parent / "superset" / "dashboards" / "bundle"
DB_YAML_PATH = "databases/Fleet_Telemetry_Warehouse_read-only.yaml"


def build_zip(bundle_dir: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(bundle_dir.rglob("*")):
            if path.is_file():
                zf.write(path, arcname=f"fleet_telemetry/{path.relative_to(bundle_dir)}")
    return buf.getvalue()


def import_dashboard(base_url: str, username: str, password: str, db_password: str) -> None:
    with httpx.Client(timeout=120) as client:
        r = client.post(
            f"{base_url}/api/v1/security/login",
            json={"username": username, "password": password, "provider": "db", "refresh": True},
        )
        r.raise_for_status()
        client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        csrf = client.get(f"{base_url}/api/v1/security/csrf_token/")
        client.headers["X-CSRFToken"] = csrf.json()["result"]

        files = {"formData": ("fleet_telemetry.zip", build_zip(BUNDLE_DIR), "application/zip")}
        data = {
            "passwords": json.dumps({DB_YAML_PATH: db_password}),
            "overwrite": "true",
        }
        r = client.post(f"{base_url}/api/v1/dashboard/import/", files=files, data=data)
        r.raise_for_status()
        print(f"Imported fleet-telemetry dashboard: {r.json()}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Import the Fleet Telemetry dashboard into Superset")
    ap.add_argument("--base-url", default=os.environ.get("SUPERSET_URL", "http://localhost:8088"))
    ap.add_argument("--username", default=os.environ.get("SUPERSET_USERNAME", "admin"))
    ap.add_argument("--password", default=os.environ.get("SUPERSET_PASSWORD", "admin"))
    ap.add_argument(
        "--db-password", default=os.environ.get("SUPERSET_RO_DB_PASSWORD", "superset_ro")
    )
    args = ap.parse_args()

    import_dashboard(args.base_url, args.username, args.password, args.db_password)


if __name__ == "__main__":
    main()
