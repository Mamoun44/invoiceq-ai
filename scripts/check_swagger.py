import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

swagger_file = (
    BASE_DIR
    / "data"
    / "invoiceq_uae_openapi.json"
)


with open(swagger_file, "r", encoding="utf-8") as file:
    swagger = json.load(file)


print("OpenAPI version:")
print(swagger.get("openapi"))

print("\nAPI title:")
print(swagger.get("info", {}).get("title"))

print("\nNumber of API paths:")
print(len(swagger.get("paths", {})))

print("\nNumber of schemas:")
print(
    len(
        swagger
        .get("components", {})
        .get("schemas", {})
    )
)