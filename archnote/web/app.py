"""FastAPI application providing a UI for the formatter."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from archnote.formatter import append_visit_to_note, format_note


BASE_DIR = Path(__file__).parent

app = FastAPI(title="Archnote Formatter", version="0.2.0")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def _base_context() -> Dict[str, Any]:
    return {
        "raw_note": "",
        "formatted_note": "",
        "existing_note": "",
        "visit_report": "",
        "visit_date": "",
        "visit_label": "",
        "updated_note": "",
        "message": "",
        "error": "",
    }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    context = _base_context()
    context["request"] = request
    return templates.TemplateResponse("index.html", context)


@app.post("/format", response_class=HTMLResponse)
async def format_view(request: Request, raw_note: str = Form(...)) -> HTMLResponse:
    context = _base_context()
    context.update({"request": request, "raw_note": raw_note})
    try:
        formatted = format_note(raw_note)
        context["formatted_note"] = formatted
        context["message"] = "Note formatted successfully."
    except Exception as exc:  # pragma: no cover - defensive for runtime issues
        context["error"] = f"Formatting failed: {exc}"
    return templates.TemplateResponse("index.html", context)


@app.post("/update", response_class=HTMLResponse)
async def update_view(
    request: Request,
    existing_note: str = Form(...),
    visit_report: str = Form(...),
    visit_date: str = Form(""),
    visit_label: str = Form(""),
) -> HTMLResponse:
    context = _base_context()
    context.update(
        {
            "request": request,
            "existing_note": existing_note,
            "visit_report": visit_report,
            "visit_date": visit_date,
            "visit_label": visit_label,
        }
    )
    try:
        updated_note = append_visit_to_note(
            existing_note,
            visit_report,
            visit_date=visit_date or None,
            visit_label=visit_label or None,
        )
        context["updated_note"] = updated_note
        context["message"] = "Visit appended successfully."
    except Exception as exc:  # pragma: no cover - defensive for runtime issues
        context["error"] = f"Unable to append visit: {exc}"
    return templates.TemplateResponse("index.html", context)


def main() -> None:  # pragma: no cover - convenience entrypoint
    import uvicorn

    host = os.getenv("ARCHNOTE_HOST", "0.0.0.0")
    port = int(os.getenv("ARCHNOTE_PORT", "8000"))
    uvicorn.run("archnote.web.app:app", host=host, port=port, reload=False)


__all__ = ["app", "main"]
