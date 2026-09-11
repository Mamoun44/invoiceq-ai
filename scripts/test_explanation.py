"""Run a sample failed invoice through the explanation service."""

import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from explanation_service import ExplanationService


def main() -> None:
    service = ExplanationService()
    result = service.explain(
        invoice={
            "invoiceNumber": "INV-1001",
            "invoiceType": "NORMAL",
        },
        invoiceq_error={
            "reason": "invoiceType",
            "errorDescription": "Invalid invoice type",
        },
        question="Why did this invoice fail?",
    )

    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
