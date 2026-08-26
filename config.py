import os
from dotenv import load_dotenv

load_dotenv()


def _get_secret(name: str, env_fallback: str, default: str = "") -> str:
    """Fetch a secret from Secret Manager when running in the cloud (GCP_PROJECT is set),
    otherwise fall back to the .env-loaded environment variable for local dev.
    """
    if os.getenv("GCP_PROJECT"):
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        project = os.getenv("GCP_PROJECT")
        resp = client.access_secret_version(name=f"projects/{project}/secrets/{name}/versions/latest")
        return resp.payload.data.decode("UTF-8")
    return os.getenv(env_fallback, default)


class Config:
    SECRET_KEY = _get_secret("flask-secret-key", "SECRET_KEY", "dev-secret-key-change-in-production")
    GEMINI_API_KEY = _get_secret("gemini-api-key", "GEMINI_API_KEY", "")
    API_KEY = _get_secret("cropguard-api-key", "API_KEY", "cropguard-api-key-change-me")

    # HuggingFace model for PlantVillage 38-class classification
    MODEL_NAME = "linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification"

    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp"}

    DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"

    # Database
    SQLALCHEMY_DATABASE_URI = _get_secret("database-url", "DATABASE_URL", "sqlite:///site.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
