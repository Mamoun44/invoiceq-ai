import json
import logging
import os
from functools import lru_cache
from typing import Any

from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import RedirectResponse, StreamingResponse
from pydantic import AliasChoices, BaseModel, Field

from analysis_tools import AnalysisResult
from stored_invoice_service import (
    InvoiceQuestion, InvoiceAnswer, InvoiceBackendError,
    SpringInvoiceBackend, StoredInvoiceService,
)
from explanation_service import (
    ExplanationService,
    FailureExplanation,
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="InvoiceQ AI Explanation Service",
    description="Anonymous InvoiceQ integration help using rules and Gemini File Search.",
    version="1.1.0",
)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


class ExplainRequest(BaseModel):
    invoice: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("invoice", "requestJson"),
    )
    invoiceqError: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("invoiceqError", "responseJson"),
    )
    question: str = Field(
        default="Why did this invoice fail?",
        min_length=1,
        max_length=2000,
    )


@lru_cache
def get_explanation_service() -> ExplanationService:
    return ExplanationService()


@app.get("/health")
def health() -> dict[str, str]:
    try:
        get_explanation_service()

        return {
            "status": "ok",
            "service": "invoiceq-ai",
        }
    except Exception:
        logger.exception("Health check failed")

        raise HTTPException(
            status_code=503,
            detail="The explanation service is not configured correctly.",
        )


@app.post(
    "/ai/explain",
    response_model=FailureExplanation,
)
def explain_failure(
    request: ExplainRequest,
) -> FailureExplanation:
    try:
        service = get_explanation_service()

        return service.explain(
            invoice=request.invoice,
            invoiceq_error=request.invoiceqError,
            question=request.question,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to generate invoice explanation")
        raise HTTPException(
            status_code=502,
            detail="Unable to generate an InvoiceQ explanation.",
        )


@app.post(
    "/ai/analyze",
    response_model=AnalysisResult,
)
def analyze_integration_context(request: ExplainRequest) -> AnalysisResult:
    """Expose the routed rule-chain result for testing and observability."""
    try:
        service = get_explanation_service()
        return service.analyze_context(
            request_json=request.invoice,
            response_json=request.invoiceqError,
            question=request.question,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to analyze InvoiceQ integration context")
        raise HTTPException(
            status_code=502,
            detail="Unable to analyze the InvoiceQ integration context.",
        )


def create_sse_event(event: str, data: dict) -> str:
    encoded_data = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {encoded_data}\n\n"


@app.post("/ai/explain/stream")
def stream_explanation(request: ExplainRequest) -> StreamingResponse:
    try:
        service = get_explanation_service()
    except Exception:
        logger.exception("Explanation service is unavailable")
        raise HTTPException(
            status_code=503,
            detail="The explanation service is unavailable.",
        )

    def generate_events():
        try:
            yield create_sse_event(
                "status",
                {"message": "Analyzing the request and InvoiceQ documentation"},
            )

            for text in service.stream_explanation(
                invoice=request.invoice,
                invoiceq_error=request.invoiceqError,
                question=request.question,
            ):
                yield create_sse_event("token", {"text": text})

            yield create_sse_event("done", {})
        except Exception:
            logger.exception("Streaming explanation failed")
            yield create_sse_event(
                "error",
                {"message": "Unable to generate the InvoiceQ explanation."},
            )

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# Path 2 has a separate access boundary and never uses the anonymous service.


@lru_cache
def get_stored_invoice_service() -> StoredInvoiceService:
    from google import genai
    from google.genai import types
    from explanation_service import MODEL

    backend_url = os.getenv("INVOICE_BACKEND_URL")
    api_key = os.getenv("GEMINI_API_KEY")
    if not backend_url or not api_key:
        raise InvoiceBackendError(503, "Stored invoice access is not configured.")
    try:
        backend = SpringInvoiceBackend(backend_url)
    except ValueError as error:
        raise InvoiceBackendError(503, "Stored invoice access is not configured.") from error
    return StoredInvoiceService(backend, genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=60000)), MODEL)


@app.post("/ai/invoices/query", response_model=InvoiceAnswer)
def query_stored_invoices(request: InvoiceQuestion, authorization: str | None = Header(default=None)) -> InvoiceAnswer:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token or any(char.isspace() for char in token):
        raise HTTPException(status_code=401, detail="Sign in to ask about stored invoices.", headers={"WWW-Authenticate": "Bearer"})
    try:
        return get_stored_invoice_service().ask(token, request.question)
    except InvoiceBackendError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error
    except Exception:
        raise HTTPException(status_code=502, detail="Unable to answer the invoice question.")
