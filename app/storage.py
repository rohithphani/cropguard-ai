"""Storage driver: local disk (dev) or GCS (cloud), selected via STORAGE_BACKEND env var."""
import os
import uuid
from flask import url_for

STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")  # "local" | "gcs"
GCS_BUCKET = os.getenv("GCS_BUCKET", "")


def save_upload(file_storage, upload_folder: str) -> tuple[str, str]:
    """Save an uploaded image via the configured backend.

    Returns (image_url, storage_key):
      - image_url:   usable directly in <img src="..."> and stored in History.image_url
      - storage_key: what's needed to re-open the file later (a local path for
                      "local", or a gs://bucket/key URI for "gcs") — used by
                      download_report() to regenerate the PDF after the initial request.
    """
    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"

    if STORAGE_BACKEND == "gcs":
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob(f"uploads/{filename}")
        file_storage.stream.seek(0)
        blob.upload_from_file(file_storage.stream, content_type=file_storage.mimetype)
        return blob.public_url, f"gs://{GCS_BUCKET}/uploads/{filename}"

    # local fallback (unchanged behaviour from before Step 7)
    filepath = os.path.join(upload_folder, filename)
    file_storage.save(filepath)
    return url_for("static", filename=f"uploads/{filename}"), filepath


def open_for_read(storage_key: str) -> str:
    """Return a local filesystem path for the given storage_key, downloading
    from GCS to a temp file first if needed. Used by generate_pdf_report(),
    which needs a real local path to embed the image in the PDF.
    """
    if storage_key.startswith("gs://"):
        import tempfile
        from google.cloud import storage
        _, _, rest = storage_key.partition("gs://")
        bucket_name, _, blob_name = rest.partition("/")
        client = storage.Client()
        blob = client.bucket(bucket_name).blob(blob_name)
        suffix = os.path.splitext(blob_name)[1]
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        blob.download_to_filename(tmp.name)
        return tmp.name

    return storage_key  # already a local filesystem path
