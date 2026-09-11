import json
import logging
from functools import lru_cache
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field

from explanation_service import (
    ExplanationService,
    FailureExplanation,
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="InvoiceQ AI Explanation Service",
    description="Explains failed InvoiceQ UAE invoices using Gemini and RAG.",
    version="1.0.0",
)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


class ExplainRequest(BaseModel):
    invoice: dict[str, Any]
    invoiceqError: dict[str, Any]
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
                {"message": "Searching InvoiceQ documentation"},
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
