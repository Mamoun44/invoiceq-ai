import requests
from pathlib import Path


SWAGGER_URL = "https://sandbox.invoiceq.com/swagger-ui/uae/specs/full.json"

BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"


def get_ref_name(ref):
    """
    Example:
    #/components/schemas/CustomerDto
    ->
    CustomerDto
    """
    return ref.split("/")[-1]


def describe_field(field_info):
    lines = []

    # Field type
    field_type = field_info.get("type")

    if field_type:
        lines.append(f"Type: {field_type}")

    # Format
    field_format = field_info.get("format")

    if field_format:
        lines.append(f"Format: {field_format}")

    # Description
    description = field_info.get("description")

    if description:
        lines.append(f"Description: {description}")

    # Allowed values
    enum = field_info.get("enum")

    if enum:
        lines.append(
            "Allowed values: " + ", ".join(map(str, enum))
        )

    # Example
    if "example" in field_info:
        lines.append(
            f"Example: {field_info['example']}"
        )

    # Referenced object
    if "$ref" in field_info:
        ref_name = get_ref_name(field_info["$ref"])
        lines.append(f"References schema: {ref_name}")

    # Arrays
    if field_info.get("type") == "array":
        items = field_info.get("items", {})

        if "$ref" in items:
            ref_name = get_ref_name(items["$ref"])
            lines.append(f"Array items: {ref_name}")

        elif "type" in items:
            lines.append(
                f"Array item type: {items['type']}"
            )

    return lines


def extract_knowledge():

    print("Getting InvoiceQ Swagger...")

    response = requests.get(
        SWAGGER_URL,
        timeout=30
    )

    response.raise_for_status()

    swagger = response.json()

    schemas = (
        swagger
        .get("components", {})
        .get("schemas", {})
    )

    KNOWLEDGE_DIR.mkdir(exist_ok=True)

    print(f"Found {len(schemas)} schemas.")

    for schema_name, schema in schemas.items():

        required_fields = schema.get("required", [])
        properties = schema.get("properties", {})

        content = []

        content.append(f"# {schema_name}")
        content.append("")

        schema_description = schema.get("description")

        if schema_description:
            content.append(schema_description)
            content.append("")

        content.append("## Fields")
        content.append("")

        for field_name, field_info in properties.items():

            content.append(f"### {field_name}")
            content.append("")

            if field_name in required_fields:
                content.append("Required: Yes")
            else:
                content.append("Required: No")

            field_details = describe_field(field_info)

            content.extend(field_details)

            content.append("")

        output_file = (
            KNOWLEDGE_DIR /
            f"{schema_name}.md"
        )

        output_file.write_text(
            "\n".join(content),
            encoding="utf-8"
        )

        print(f"Created: {output_file.name}")

    print("\nKnowledge extraction finished.")


if __name__ == "__main__":
    extract_knowledge()