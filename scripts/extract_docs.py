import requests
from bs4 import BeautifulSoup
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"


DOCUMENTS = {
    "outward_invoice_rules": (
        "https://sandbox.invoiceq.com/"
        "swagger-ui/uae/documents/outward-invoice.html"
    ),

    "lookups": (
        "https://sandbox.invoiceq.com/"
        "swagger-ui/uae/reference/lookups.html"
    ),
}


def extract_page(url):

    response = requests.get(
        url,
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    lines = []

    # Extract useful documentation elements
    for element in soup.find_all(
        ["h1", "h2", "h3", "p", "li"]
    ):

        text = element.get_text(
            " ",
            strip=True
        )

        if not text:
            continue

        if element.name == "h1":
            lines.append(f"# {text}")

        elif element.name == "h2":
            lines.append(f"## {text}")

        elif element.name == "h3":
            lines.append(f"### {text}")

        elif element.name == "li":
            lines.append(f"- {text}")

        else:
            lines.append(text)

        lines.append("")

    return "\n".join(lines)


def main():

    KNOWLEDGE_DIR.mkdir(
        exist_ok=True
    )

    for name, url in DOCUMENTS.items():

        print(f"Reading: {url}")

        content = extract_page(url)

        output_file = (
            KNOWLEDGE_DIR /
            f"{name}.md"
        )

        output_file.write_text(
            content,
            encoding="utf-8"
        )

        print(
            f"Created: {output_file.name}"
        )


if __name__ == "__main__":
    main()