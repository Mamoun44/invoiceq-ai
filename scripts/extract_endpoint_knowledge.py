import requests
from pathlib import Path


SWAGGER_URL = "https://sandbox.invoiceq.com/swagger-ui/uae/specs/full.json"

TARGET_PATH = "/api/external/v2/outward-invoice/create"
METHOD = "post"

BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"


def get_ref_name(ref):
    if not ref:
        return None

    return ref.split("/")[-1]


def extract_endpoint():

    print("Reading InvoiceQ Swagger...")

    response = requests.get(
        SWAGGER_URL,
        timeout=30
    )

    response.raise_for_status()

    swagger = response.json()

    operation = swagger["paths"][TARGET_PATH][METHOD]

    content = []

    # Title
    content.append("# Create Outward Invoice")
    content.append("")

    # Method and path
    content.append(f"Method: {METHOD.upper()}")
    content.append(f"Path: {TARGET_PATH}")
    content.append("")

    # Summary
    summary = operation.get("summary")

    if summary:
        content.append(f"Summary: {summary}")
        content.append("")

    # Description
    description = operation.get("description")

    if description:
        content.append(f"Description: {description}")
        content.append("")

    # Request schema
    request_schema = (
        operation
        .get("requestBody", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
    )

    request_ref = request_schema.get("$ref")

    if request_ref:
        content.append(
            f"Request schema: {get_ref_name(request_ref)}"
        )
        content.append("")

    # Responses
    content.append("## Responses")
    content.append("")

    responses = operation.get("responses", {})

    for status_code, response_info in responses.items():

        description = response_info.get(
            "description",
            "No description"
        )

        content.append(f"### HTTP {status_code}")
        content.append(description)

        response_schema = (
            response_info
            .get("content", {})
            .get("application/json", {})
            .get("schema", {})
        )

        response_ref = response_schema.get("$ref")

        if response_ref:
            content.append(
                f"Response schema: {get_ref_name(response_ref)}"
            )

        content.append("")

    # Save file
    KNOWLEDGE_DIR.mkdir(exist_ok=True)

    output_file = (
        KNOWLEDGE_DIR /
        "outward_invoice_create.md"
    )

    output_file.write_text(
        "\n".join(content),
        encoding="utf-8"
    )

    print(f"Created: {output_file}")


if __name__ == "__main__":
    extract_endpoint()