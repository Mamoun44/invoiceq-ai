from pathlib import Path
import requests


SWAGGER_URL = (
    "https://sandbox.invoiceq.com/swagger-ui/uae/specs/full.json"
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_FILE = DATA_DIR / "invoiceq_uae_openapi.json"


def download_swagger():
    DATA_DIR.mkdir(exist_ok=True)

    response = requests.get(SWAGGER_URL, timeout=30)

    response.raise_for_status()

    OUTPUT_FILE.write_text(
        response.text,
        encoding="utf-8"
    )

    print("Swagger downloaded successfully.")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    download_swagger()