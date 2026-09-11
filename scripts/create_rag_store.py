import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY was not found in .env")

client = genai.Client(api_key=api_key)


BASE_DIR = Path(__file__).resolve().parent.parent

KNOWLEDGE_DIR = BASE_DIR / "knowledge"

STORE_FILE = BASE_DIR / "store_name.txt"


def create_store():

    print("Creating InvoiceQ File Search store...")

    store = client.file_search_stores.create(
        config={
            "display_name": "invoiceq-uae-knowledge",
            "embedding_model": "models/gemini-embedding-2",
        }
    )

    print("Created store:")
    print(store.name)

    return store


def upload_file(store, file_path):

    print(f"Uploading: {file_path.name}")

    operation = (
        client.file_search_stores
        .upload_to_file_search_store(
            file=str(file_path),
            file_search_store_name=store.name,
            config={
                "display_name": file_path.name
            }
        )
    )

    while not operation.done:

        time.sleep(2)

        operation = client.operations.get(
            operation
        )

    print(f"Indexed: {file_path.name}")


def main():

    store = create_store()

    files = list(
        KNOWLEDGE_DIR.glob("*.md")
    )

    if not files:
        raise ValueError(
            "No Markdown files found in knowledge/"
        )

    print(
        f"\nFound {len(files)} knowledge files.\n"
    )

    for file_path in files:

        upload_file(
            store,
            file_path
        )

    STORE_FILE.write_text(
        store.name,
        encoding="utf-8"
    )

    print("\nFinished.")
    print(f"Store name: {store.name}")
    print("Saved store name to store_name.txt")


if __name__ == "__main__":
    main()