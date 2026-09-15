"""Deterministic tools and flexible rule chain for anonymous integration help."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

from invoice_validation import InvoiceBusinessRule


IntentName = Literal[
    "explain_failure",
    "explain_error",
    "validate_request",
    "request_fact",
    "invoiceq_rule",
    "stored_invoice_query",
    "unrelated",
]


class IntentDecision(BaseModel):
    """The LLM router's constrained decision."""

    intent: IntentName
    reason: str = Field(max_length=300)


class AnalysisProblem(BaseModel):
    """One concrete issue found by the deterministic analysis tool."""

    field: str | None = None
    providedValue: Any = None
    reason: str
    recommendedAction: str
    evidenceSource: Literal[
        "invoiceq_response",
        "openapi_schema",
        "invoiceq_documentation",
        "request_rule",
        "unknown",
    ]


class MatchedRule(BaseModel):
    """One documented InvoiceQ rule returned by the File Search tool."""

    rule: str
    source: str | None = None
    fields: list[str] = Field(default_factory=list)
    recommendedAction: str | None = None


class KnowledgeProblem(BaseModel):
    """A validation problem found by the File Search knowledge tool."""

    field: str | None = None
    reason: str
    recommendedAction: str
    source: str | None = None


class KnowledgeAssessment(BaseModel):
    """Constrained output produced by Gemini while using File Search."""

    matchedRules: list[MatchedRule] = Field(default_factory=list)
    documentedProblems: list[KnowledgeProblem] = Field(default_factory=list)
    documentationSufficient: bool


class AnalysisResult(BaseModel):
    """Stable JSON contract between the tool layer and the final LLM."""

    intent: IntentName
    status: Literal["failure", "success", "unknown", "not_allowed"]
    httpStatus: int | None = None
    problems: list[AnalysisProblem] = Field(default_factory=list)
    facts: dict[str, Any] = Field(default_factory=dict)
    matchedRules: list[MatchedRule] = Field(default_factory=list)
    knowledgeStatus: Literal["matched", "no_match", "not_needed", "unavailable"] = (
        "not_needed"
    )
    missingContext: list[str] = Field(default_factory=list)
    needsMoreInformation: bool = False


@dataclass
class RuleContext:
    intent: IntentName
    request_json: dict[str, Any] | None
    response_json: dict[str, Any] | None
    question: str


@dataclass
class RuleState:
    status: Literal["failure", "success", "unknown", "not_allowed"] = "unknown"
    http_status: int | None = None
    problems: list[AnalysisProblem] = field(default_factory=list)
    facts: dict[str, Any] = field(default_factory=dict)
    missing_context: list[str] = field(default_factory=list)


class AnalysisRule(Protocol):
    """A replaceable step in the integration analysis chain."""

    def apply(self, context: RuleContext, state: RuleState) -> None: ...


class AccessBoundaryRule:
    """Prevent anonymous requests from pretending stored data is available."""

    def apply(self, context: RuleContext, state: RuleState) -> None:
        if context.intent == "stored_invoice_query":
            state.status = "not_allowed"
            state.missing_context.append("authenticated customer context")


class ContextAvailabilityRule:
    def apply(self, context: RuleContext, state: RuleState) -> None:
        if context.intent in {"explain_failure", "validate_request", "request_fact"}:
            if context.request_json is None:
                state.missing_context.append("requestJson")
        if context.intent in {"explain_failure", "explain_error"}:
            if not context.response_json:
                state.missing_context.append("responseJson")


class ResponseStatusRule:
    def apply(self, context: RuleContext, state: RuleState) -> None:
        response = context.response_json
        if not response:
            return

        status = _first_int(response, "httpStatus", "statusCode", "status")
        state.http_status = status
        if status is not None:
            state.facts["httpStatus"] = status

        valid = response.get("valid")
        if valid is False or (status is not None and status >= 400):
            state.status = "failure"
        elif valid is True or (status is not None and 200 <= status < 300):
            state.status = "success"


class ResponseErrorRule:
    def apply(self, context: RuleContext, state: RuleState) -> None:
        response = context.response_json
        if not response:
            return

        for raw_error in _collect_errors(response):
            reason = _error_text(raw_error)
            if not reason:
                continue
            field_path = _error_field(raw_error)
            provided_value, found = _find_request_value(
                context.request_json, field_path
            )
            state.problems.append(
                AnalysisProblem(
                    field=field_path,
                    providedValue=provided_value if found else None,
                    reason=reason,
                    recommendedAction=_recommend_action(
                        field_path, provided_value, found, reason
                    ),
                    evidenceSource="invoiceq_response",
                )
            )

        if state.problems:
            state.status = "failure"


class OpenApiSchemaRule:
    """Validate every supplied field recursively against the IQ OpenAPI schema."""

    def __init__(self, specification_path: Path | None = None) -> None:
        path = specification_path or (
            Path(__file__).resolve().parent / "data" / "invoiceq_uae_openapi.json"
        )
        self.specification = json.loads(path.read_text(encoding="utf-8"))
        operation = self.specification["paths"][
            "/api/external/v2/outward-invoice/create"
        ]["post"]
        self.request_schema = operation["requestBody"]["content"][
            "application/json"
        ]["schema"]

    def apply(self, context: RuleContext, state: RuleState) -> None:
        if context.request_json is None:
            return
        if context.intent not in {"validate_request", "explain_failure"}:
            return

        before = len(state.problems)
        self._validate_value(
            value=context.request_json,
            schema=self.request_schema,
            path="",
            required_value=True,
            problems=state.problems,
        )
        if len(state.problems) > before:
            state.status = "failure"

    def _resolve(self, schema: dict[str, Any]) -> dict[str, Any]:
        reference = schema.get("$ref")
        if not reference:
            return schema
        current: Any = self.specification
        for token in reference.removeprefix("#/").split("/"):
            current = current[token]
        return current

    def _validate_value(
        self,
        *,
        value: Any,
        schema: dict[str, Any],
        path: str,
        required_value: bool,
        problems: list[AnalysisProblem],
    ) -> None:
        schema = self._resolve(schema)
        expected_type = schema.get("type")
        enum_values = schema.get("enum")

        if value is None and schema.get("nullable"):
            return

        if required_value and _is_empty(value) and expected_type != "object":
            problems.append(
                self._problem(
                    path,
                    value,
                    "The required value is missing or empty.",
                    f"Provide a non-empty value for {path or 'the request'}.",
                )
            )
            return

        if enum_values and not _enum_contains(enum_values, value):
            allowed = ", ".join(str(item) for item in enum_values)
            problems.append(
                self._problem(
                    path,
                    value,
                    f"The value is not allowed. Allowed values: {allowed}.",
                    f"Use one of the allowed values for {path}: {allowed}.",
                )
            )
            return

        if not _matches_type(expected_type, value, enum_values):
            problems.append(
                self._problem(
                    path,
                    value,
                    f"The value must have type {expected_type}.",
                    f"Provide {path or 'the request'} as {expected_type}.",
                )
            )
            return

        if expected_type == "object" or "properties" in schema:
            if not isinstance(value, dict):
                return
            properties = schema.get("properties", {})
            required_fields = list(schema.get("required", []))
            # The shared adjustment schema describes document-level taxType;
            # on line adjustments it is explicitly ignored by InvoiceQ.
            if re.search(r"\.line(?:Allowances|Charges)\[\d+\]$", path):
                required_fields = [name for name in required_fields if name != "taxType"]
            for field_name in required_fields:
                child_path = _join_path(path, field_name)
                if field_name not in value:
                    problems.append(
                        self._problem(
                            child_path,
                            None,
                            "The required field is missing.",
                            f"Add the required field {child_path}.",
                        )
                    )
            for field_name, child_value in value.items():
                child_schema = properties.get(field_name)
                if not isinstance(child_schema, dict):
                    continue
                self._validate_value(
                    value=child_value,
                    schema=child_schema,
                    path=_join_path(path, field_name),
                    required_value=field_name in required_fields,
                    problems=problems,
                )

        if expected_type == "array" and isinstance(value, list):
            if required_value and not value:
                # The empty-value check above normally handles this branch.
                return
            item_schema = schema.get("items")
            if isinstance(item_schema, dict):
                for index, item in enumerate(value):
                    self._validate_value(
                        value=item,
                        schema=item_schema,
                        path=f"{path}[{index}]",
                        required_value=True,
                        problems=problems,
                    )

        if expected_type == "string" and isinstance(value, str):
            if schema.get("format") == "date-time" and not _valid_datetime(value):
                problems.append(
                    self._problem(
                        path,
                        value,
                        "The value is not a valid ISO 8601 date-time.",
                        f"Provide {path} in ISO 8601 date-time format.",
                    )
                )

        if expected_type == "integer" and isinstance(value, int) and not isinstance(value, bool):
            bits = {"int32": 32, "int64": 64}.get(schema.get("format"))
            if bits and not -(2 ** (bits - 1)) <= value < 2 ** (bits - 1):
                problems.append(self._problem(path, value, f"The value exceeds {schema['format']} range.", "Use an integer within the documented range."))

    @staticmethod
    def _problem(
        path: str,
        value: Any,
        reason: str,
        action: str,
    ) -> AnalysisProblem:
        return AnalysisProblem(
            field=path or None,
            providedValue=value,
            reason=reason,
            recommendedAction=action,
            evidenceSource="openapi_schema",
        )


class RequestedFactRule:
    def apply(self, context: RuleContext, state: RuleState) -> None:
        if context.intent != "request_fact" or context.request_json is None:
            return

        question = context.question.casefold()
        common_fields = {
            "invoice number": "invoiceNumber",
            "invoice id": "invoiceNumber",
            "currency": "currencyIsoCode",
            "total amount": "totalInvoiceAmount",
            "invoice type": "invoiceType",
        }
        for phrase, field_name in common_fields.items():
            if phrase in question and field_name in context.request_json:
                state.facts[field_name] = context.request_json[field_name]


class IntegrationAnalysisTool:
    """Runs an ordered, replaceable chain and returns normalized JSON."""

    def __init__(self, rules: list[AnalysisRule] | None = None) -> None:
        self.rules = rules if rules is not None else [
            AccessBoundaryRule(),
            ContextAvailabilityRule(),
            ResponseStatusRule(),
            ResponseErrorRule(),
            OpenApiSchemaRule(),
            InvoiceBusinessRule(),
            RequestedFactRule(),
        ]

    def execute(
        self,
        *,
        intent: IntentName,
        request_json: dict[str, Any] | None,
        response_json: dict[str, Any] | None,
        question: str,
    ) -> AnalysisResult:
        context = RuleContext(intent, request_json, response_json, question)
        state = RuleState()
        for rule in self.rules:
            rule.apply(context, state)
            if state.status == "not_allowed":
                break

        if intent == "validate_request" and context.request_json is not None:
            state.facts["validationScope"] = "Bundled UAE create-invoice schema and documented local business rules; server acceptance is not verified."
            state.facts["localValidationPassed"] = not state.problems

        needs_more_information = bool(state.missing_context)
        if not state.problems and state.status == "unknown" and intent in {
            "explain_failure",
            "explain_error",
            "validate_request",
        }:
            needs_more_information = True

        return AnalysisResult(
            intent=intent,
            status=state.status,
            httpStatus=state.http_status,
            problems=state.problems,
            facts=state.facts,
            missingContext=state.missing_context,
            needsMoreInformation=needs_more_information,
        )


def fallback_intent(
    question: str,
    request_json: dict[str, Any] | None,
    response_json: dict[str, Any] | None,
) -> IntentDecision:
    """Deterministic fallback used only if the LLM router is unavailable."""

    text = question.casefold()
    if any(
        phrase in text
        for phrase in (
            "all my invoices",
            "my stored invoices",
            "invoice with id",
            "invoice id 0",
            "total amount i have",
        )
    ):
        return IntentDecision(
            intent="stored_invoice_query",
            reason="The question requests stored customer invoice data.",
        )
    if any(phrase in text for phrase in ("recipe", "weather", "football", "movie")):
        return IntentDecision(
            intent="unrelated",
            reason="The question is unrelated to InvoiceQ integration.",
        )
    if "what does" in text and ("error" in text or "response" in text):
        return IntentDecision(
            intent="explain_error",
            reason="The user asks for the meaning of the supplied response.",
        )
    if "why" in text and any(word in text for word in ("fail", "failed", "reject")):
        return IntentDecision(
            intent="explain_failure",
            reason="The user asks why the supplied request failed.",
        )
    if any(word in text for word in ("validate", "check", "correct request")):
        return IntentDecision(
            intent="validate_request",
            reason="The user asks to inspect the supplied request.",
        )
    if any(
        phrase in text
        for phrase in ("invoice number", "invoice id", "currency", "total amount")
    ) and request_json is not None:
        return IntentDecision(
            intent="request_fact",
            reason="The answer is a value in the supplied request.",
        )
    if response_json is not None:
        return IntentDecision(
            intent="explain_failure",
            reason="A response is supplied and the question concerns the request.",
        )
    if request_json is not None:
        return IntentDecision(
            intent="validate_request",
            reason="Only request context is available.",
        )
    return IntentDecision(
        intent="invoiceq_rule",
        reason="No request or response context was supplied.",
    )


def _join_path(parent: str, child: str) -> str:
    return f"{parent}.{child}" if parent else child


def _is_empty(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip()) or value == []


def _enum_contains(allowed: list[Any], value: Any) -> bool:
    # The bundled paymentMeans integer schema encodes its enum as strings.
    if isinstance(value, bool):
        return any(isinstance(item, bool) and item == value for item in allowed)
    return any(item == value or (isinstance(value, int) and isinstance(item, str) and str(value) == item) for item in allowed)


def _matches_type(expected: str | None, value: Any, enum_values: Any = None) -> bool:
    return {
        "string": lambda: isinstance(value, str),
        "integer": lambda: isinstance(value, int) and not isinstance(value, bool),
        "number": lambda: isinstance(value, (int, float)) and not isinstance(value, bool) and (not isinstance(value, float) or math.isfinite(value)),
        "boolean": lambda: isinstance(value, bool),
        "object": lambda: isinstance(value, dict),
        "array": lambda: isinstance(value, list),
    }.get(expected, lambda: True)()


def _valid_datetime(value: str) -> bool:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", value):
        return False
    if value[-1] != "Z" and (int(value[-5:-3]) > 23 or int(value[-2:]) > 59):
        return False
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None
    except ValueError:
        return False


def _first_int(data: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return None


def _collect_errors(response: dict[str, Any]) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    errors = response.get("errors")
    if isinstance(errors, list):
        for error in errors:
            if isinstance(error, dict):
                collected.append(error)
            elif isinstance(error, str):
                collected.append({"message": error})
    elif isinstance(errors, dict):
        collected.append(errors)

    nested_error = response.get("error")
    if isinstance(nested_error, dict):
        collected.append(nested_error)
    elif isinstance(nested_error, str):
        collected.append({"message": nested_error})

    status = _first_int(response, "httpStatus", "statusCode", "status")
    successful = response.get("valid") is True or (status is not None and 200 <= status < 300 and response.get("valid") is not False)
    if not collected and not successful and any(
        key in response
        for key in ("reason", "errorDescription", "message", "detail")
    ):
        collected.append(response)
    return collected


def _error_text(error: dict[str, Any]) -> str:
    for key in ("errorDescription", "message", "detail", "description", "reason"):
        value = error.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _error_field(error: dict[str, Any]) -> str | None:
    for key in ("field", "fieldPath", "path", "reason", "property"):
        value = error.get(key)
        if not isinstance(value, str) or not value.strip():
            continue
        candidate = value.strip()
        if key == "reason" and " " in candidate:
            continue
        return _normalize_path(candidate)
    return None


def _normalize_path(path: str) -> str:
    path = path.strip().lstrip("$/.")
    for prefix in ("requestJson.", "invoice.", "body."):
        if path.startswith(prefix):
            path = path[len(prefix) :]
    return path


def _find_request_value(
    request_json: dict[str, Any] | None, field_path: str | None
) -> tuple[Any, bool]:
    if request_json is None or not field_path:
        return None, False

    tokens = re.findall(r"[^.\[\]]+", field_path)
    current: Any = request_json
    try:
        for token in tokens:
            if isinstance(current, dict):
                current = current[token]
            elif isinstance(current, list) and token.isdigit():
                current = current[int(token)]
            else:
                return None, False
        return current, True
    except (KeyError, IndexError):
        pass

    leaf = tokens[-1] if tokens else field_path
    matches: list[Any] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key == leaf:
                    matches.append(child)
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(request_json)
    return (matches[0], True) if len(matches) == 1 else (None, False)


def _recommend_action(
    field_path: str | None,
    value: Any,
    value_found: bool,
    reason: str,
) -> str:
    field_label = field_path or "the affected field"
    normalized_reason = reason.casefold()
    if field_path == "products" and value_found and isinstance(value, list) and not value:
        return "Add at least one valid product to products."
    if any(word in normalized_reason for word in ("missing", "required", "empty")):
        return f"Provide a valid value for {field_label}."
    if any(word in normalized_reason for word in ("invalid", "not allowed", "unsupported")):
        return f"Replace {field_label} with a value allowed by InvoiceQ."
    return f"Correct {field_label} according to the InvoiceQ error response."
