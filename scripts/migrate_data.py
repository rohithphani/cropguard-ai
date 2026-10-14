"""Milestone 4: copy CropGuard data from the old on-VM SQLite database (Milestone 3)
into Cloud SQL (PostgreSQL), and the old local uploads into the private GCS bucket.

Run INSIDE the v2 container on the VM, after `flask db upgrade` has created the tables:

    docker run --rm \
      -e GCP_PROJECT=cropguard-ai-509423 -e STORAGE_BACKEND=gcs -e GCS_BUCKET=<bucket> \
      -v cropguard_db:/old/instance -v cropguard_uploads:/old/uploads \
      <image>:v2 python scripts/migrate_data.py /old/instance/site.db /old/uploads

The target DATABASE_URL is read from Secret Manager (see config.py); no credentials
are passed on the command line. Safe to re-run: rows that already exist are skipped.
"""
import os
import sys

from sqlalchemy import create_engine, MetaData, select, func, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config  # noqa: E402

TABLES = ["user", "history"]  # parents before children (history.user_id -> user.id)


def counts(engine, meta):
    with engine.connect() as c:
        return {t: c.execute(select(func.count()).select_from(meta.tables[t])).scalar() for t in TABLES}


def main(src_db, uploads_dir):
    src = create_engine(f"sqlite:///{src_db}")
    dst = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    smeta, dmeta = MetaData(), MetaData()
    smeta.reflect(src, only=TABLES)
    dmeta.reflect(dst, only=TABLES)

    bucket_name = os.getenv("GCS_BUCKET", "")
    bucket = None
    if bucket_name:
        from google.cloud import storage
        bucket = storage.Client().bucket(bucket_name)

    copied_files = 0
    with src.connect() as s, dst.begin() as d:
        for t in TABLES:
            existing = {r[0] for r in d.execute(select(dmeta.tables[t].c.id))}
            for row in s.execute(select(smeta.tables[t])).mappings():
                if row["id"] in existing:
                    continue
                data = dict(row)
                if t == "history" and bucket is not None:
                    url = data.get("image_url") or ""
                    name = url.rsplit("/", 1)[-1]
                    if url.startswith("/static/uploads/") and name:
                        local = os.path.join(uploads_dir, name)
                        if os.path.exists(local):
                            bucket.blob(f"uploads/{name}").upload_from_filename(local)
                            copied_files += 1
                        data["image_url"] = f"/uploads/{name}"
                d.execute(dmeta.tables[t].insert().values(**data))
        # keep PostgreSQL SERIAL sequences ahead of the copied ids
        for t in (TABLES if dst.dialect.name == "postgresql" else []):
            d.execute(text(
                f"SELECT setval(pg_get_serial_sequence('\"{t}\"','id'), "
                f"COALESCE((SELECT MAX(id) FROM \"{t}\"), 1), (SELECT COUNT(*) FROM \"{t}\") > 0)"))

    before, after = counts(src, smeta), counts(dst, dmeta)
    print()
    print("ROW COUNTS  (old: SQLite on VM  vs  new: Cloud SQL PostgreSQL)")
    print(f"{'table':<10}{'old SQLite':>12}{'Cloud SQL':>12}   match")
    for t in TABLES:
        ok = "YES" if before[t] == after[t] else "NO"
        print(f"{t:<10}{before[t]:>12}{after[t]:>12}   {ok}")
    print(f"\nupload files copied to gs://{bucket_name}/uploads/: {copied_files}")
    if before != after:
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python scripts/migrate_data.py <old_sqlite_db> <old_uploads_dir>")
    main(sys.argv[1], sys.argv[2])
