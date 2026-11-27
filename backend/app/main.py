"""FastAPI entrypoint for the LekhX offline multilingual office platform."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .assistant import generate_document
from .config import ALLOWED_ORIGINS, APP_NAME, APP_VERSION, DIST_DIR, EXPORTS_DIR, HF_DATASET_REPO, HF_DATASET_URL
from .db import get_generated_document, get_setting, initialize_database, list_generated_documents, set_setting
from .hardware_profile import ensure_hardware_profile
from .model_catalog import list_models, set_active_model
from .model_runtime import probe_llm_runtime
from .office_templates import load_languages, load_templates
from .reference_knowledge import ingest_reference_datasets
from .schemas import GenerateDocumentRequest, SettingsUpdateRequest
from .updates import check_remote_updates, get_local_update_status


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_database()
    ingest_reference_datasets()
    ensure_hardware_profile()
    yield


app = FastAPI(
    title=f"{APP_NAME} API",
    version=APP_VERSION,
    description="Offline-first multilingual AI office generator for doc, pdf, excel, powerpoint, and notes.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, object]:
    """Return backend health, hardware tier, llama.cpp reachability, and HF repo target."""

    hardware = ensure_hardware_profile()
    llm_status = probe_llm_runtime()
    return {
        "status": "ok",
        "app": APP_NAME,
        "version": APP_VERSION,
        "huggingface_repo": HF_DATASET_REPO,
        "dataset_url": HF_DATASET_URL,
        "hardware": hardware.to_json_dict(),
        "llm_runtime": llm_status,
    }


@app.get("/api/languages")
def get_languages() -> dict[str, object]:
    """List supported office localization packs."""

    return {"languages": load_languages()}


@app.get("/api/templates")
def get_templates(format: str | None = None) -> dict[str, object]:
    """List built-in and custom templates, optionally filtered by office format."""

    return {"templates": load_templates(office_format=format)}


@app.get("/api/documents")
def get_documents(limit: int = 50) -> dict[str, object]:
    """List generated office files recorded in local SQLite."""

    return {"documents": list_generated_documents(limit=limit)}


@app.post("/api/generate")
def generate(request: GenerateDocumentRequest):
    """Plan and generate a verified `.docx`, `.pdf`, `.xlsx`, `.pptx`, or `.md` artifact."""

    try:
        return generate_document(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/documents/{document_id}/download")
def download_document(document_id: str):
    """Stream a generated office artifact safely from `EXPORTS_DIR`."""

    record = get_generated_document(document_id)
    if not record:
        raise HTTPException(status_code=404, detail="Generated document not found.")
    exports_root = EXPORTS_DIR.resolve()
    file_path = (exports_root / str(record["relative_path"])).resolve()
    if exports_root not in file_path.parents or not file_path.is_file() or file_path.is_symlink():
        raise HTTPException(status_code=404, detail="Generated artifact file is unavailable.")
    return FileResponse(path=str(file_path), filename=str(record["filename"]))


@app.get("/api/models")
def get_models() -> dict[str, object]:
    """Return cataloged and locally installed GGUF models."""

    return list_models()


@app.get("/api/settings")
def get_settings() -> dict[str, object]:
    """Read workspace settings and active model selection."""

    return {
        "default_format": get_setting("default_format", "doc"),
        "default_language": get_setting("default_language", "en"),
        "active_model": get_setting("active_model", "lekhx-1.0.0"),
        "llm_base_url": get_setting("llm_base_url", "http://127.0.0.1:8080/v1"),
    }


@app.post("/api/settings")
def update_settings(payload: SettingsUpdateRequest) -> dict[str, object]:
    """Persist user preferences inside local SQLite."""

    if payload.default_format is not None:
        set_setting("default_format", payload.default_format)
    if payload.default_language is not None:
        set_setting("default_language", payload.default_language.strip().lower())
    if payload.active_model is not None:
        set_active_model(payload.active_model)
    if payload.llm_base_url is not None:
        set_setting("llm_base_url", payload.llm_base_url.strip())
    return get_settings()


@app.get("/api/updates/status")
def updates_status(check_remote: bool = False) -> dict[str, object]:
    """Report current app/dataset version and optional remote drishtijs/LekhX manifest check."""

    if check_remote:
        return check_remote_updates()
    return get_local_update_status()


if (DIST_DIR / "index.html").is_file():
    app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="spa")
elif (Path(__file__).resolve().parents[2] / "index.html").is_file():
    root_dir = Path(__file__).resolve().parents[2]
    app.mount("/app", StaticFiles(directory=str(root_dir / "app")), name="drishti_app")
    app.mount("/public", StaticFiles(directory=str(root_dir / "public")), name="drishti_public")
