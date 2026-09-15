"""Smoke-test Gemini generation and the existing InvoiceQ File Search store."""

import os
import sys
import traceback
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types


BASE_DIR = Path(__file__).resolve().parent.parent
STORE_FILE = BASE_DIR / "store_name.txt"
load_dotenv(BASE_DIR / ".env")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
TIMEOUT_MS = int(os.getenv("GEMINI_TIMEOUT_MS", "120000"))


def run_test(label: str, request) -> bool:
    print(f"\n{label}", flush=True)
    try:
        response = request()
        if not response.text:
            raise RuntimeError("Gemini returned an empty response.")
        print(response.text.strip(), flush=True)
        return True
    except Exception:
        traceback.print_exc()
        return False


def main() -> int:
    print("TEST SCRIPT STARTED", flush=True)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(f"GEMINI_API_KEY is missing from {BASE_DIR / '.env'}")
    if not STORE_FILE.is_file():
        raise FileNotFoundError(f"File Search store name is missing: {STORE_FILE}")

    store_name = STORE_FILE.read_text(encoding="utf-8").strip()
    if not store_name:
        raise RuntimeError(f"File Search store name is empty: {STORE_FILE}")

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=TIMEOUT_MS),
    )

    print(f"Model: {MODEL}")
    print(f"Timeout: {TIMEOUT_MS / 1000:g} seconds")
    print(f"Store: {store_name}")

    try:
        store = client.file_search_stores.get(name=store_name)
        print(f"Active documents: {store.active_documents_count}")
    except Exception:
        print("\nSTORE CHECK ERROR:", file=sys.stderr)
        traceback.print_exc()
        return 1

    normal_ok = run_test(
        "TEST 1: Gemini without File Search",
        lambda: client.models.generate_content(
            model=MODEL,
            contents="Reply only with the word OK.",
            config=types.GenerateContentConfig(
                temperature=0,
                max_output_tokens=256,
                thinking_config=types.ThinkingConfig(
                    thinking_level=types.ThinkingLevel.LOW,
                ),
            ),
        ),
    )

    if not normal_ok:
        print(
            "\nSkipping RAG: ordinary model generation failed, so File Search "
            "cannot be tested meaningfully.",
            file=sys.stderr,
        )
        return 1

    rag_ok = run_test(
        "TEST 2: Gemini with File Search",
        lambda: client.models.generate_content(
            model=MODEL,
            contents=(
                "According to the uploaded InvoiceQ documentation, what are the "
                "allowed values for invoiceType? Answer only from the uploaded "
                "documentation."
            ),
            config=types.GenerateContentConfig(
                temperature=0,
                thinking_config=types.ThinkingConfig(
                    thinking_level=types.ThinkingLevel.LOW,
                ),
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[store_name],
                            top_k=3,
                        )
                    )
                ],
            ),
        ),
    )

    return 0 if rag_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
