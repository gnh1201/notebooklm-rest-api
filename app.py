# Google NotebookLM REST Gateway API
# https://github.com/gnh1201/notebooklm-rest-api
import os
import uuid
import tempfile
from typing import Any, Optional, Literal, Dict

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel

from notebooklm import NotebookLMClient, RPCError  # notebooklm-py :contentReference[oaicite:2]{index=2}


# ----------------------------
# Config / Security
# ----------------------------
API_KEY = os.environ.get("NOTEBOOKLM_REST_API_KEY", "")  # set this in production
AUTH_STORAGE_PATH = os.environ.get("NOTEBOOKLM_STORAGE_PATH")  # optional override


def require_api_key(x_api_key: Optional[str] = None):
    # Minimal API-key gate. Put this behind a real gateway (Cloudflare, Nginx, etc.) for production.
    if API_KEY:
        # FastAPI header parsing without extra imports (keep simple):
        # Prefer: from fastapi import Header; def require_api_key(x_api_key: str = Header(None)) ...
        # but we keep it minimal and rely on query param fallback too.
        if x_api_key != API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")


async def get_client() -> NotebookLMClient:
    """
    Creates a client using notebooklm-py's supported auth precedence:
    - explicit path to from_storage()
    - NOTEBOOKLM_AUTH_JSON
    - NOTEBOOKLM_HOME/storage_state.json
    - ~/.notebooklm/storage_state.json
    :contentReference[oaicite:3]{index=3}
    """
    try:
        if AUTH_STORAGE_PATH:
            return await NotebookLMClient.from_storage(AUTH_STORAGE_PATH)
        return await NotebookLMClient.from_storage()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize NotebookLM client: {e}")


def map_rpc_error(e: RPCError) -> HTTPException:
    # notebooklm-py raises RPCError for API failures :contentReference[oaicite:4]{index=4}
    msg = str(e)
    if "401" in msg or "403" in msg or "auth" in msg.lower():
        return HTTPException(status_code=401, detail=msg)
    if "rate" in msg.lower() or "429" in msg:
        return HTTPException(status_code=429, detail=msg)
    return HTTPException(status_code=502, detail=msg)


# ----------------------------
# Models
# ----------------------------
class NotebookCreateReq(BaseModel):
    title: str


class NotebookRenameReq(BaseModel):
    new_title: str


class SourceAddUrlReq(BaseModel):
    url: str
    wait: bool = True


class SourceAddTextReq(BaseModel):
    title: str
    content: str


class SourceAddYoutubeReq(BaseModel):
    url: str
    wait: bool = True


class ChatAskReq(BaseModel):
    question: str
    # optional persona fields could be added if you want


class ArtifactGenerateReq(BaseModel):
    # A simple unified generator:
    # audio/video/report/quiz/flashcards/slide_deck/infographic/data_table/mind_map
    type: Literal[
        "audio",
        "video",
        "report",
        "quiz",
        "flashcards",
        "slide_deck",
        "infographic",
        "data_table",
        "mind_map",
    ]
    # Options are passed through as-is to the underlying generate_* calls where applicable.
    # (The library supports many per-type options; keep this generic.)
    options: Dict[str, Any] = {}


class TaskPollResp(BaseModel):
    ok: bool
    status: Any


# ----------------------------
# App
# ----------------------------
app = FastAPI(title="NotebookLM REST API (powered by notebooklm-py)")


@app.get("/health")
async def health():
    return {"ok": True}


# ----------------------------
# Notebooks
# ----------------------------
@app.get("/v1/notebooks")
async def list_notebooks():
    client = await get_client()
    async with client:
        try:
            nbs = await client.notebooks.list()
            return {"ok": True, "items": [nb.model_dump() if hasattr(nb, "model_dump") else nb.__dict__ for nb in nbs]}
        except RPCError as e:
            raise map_rpc_error(e)


@app.post("/v1/notebooks")
async def create_notebook(req: NotebookCreateReq):
    client = await get_client()
    async with client:
        try:
            nb = await client.notebooks.create(req.title)
            return {"ok": True, "notebook": nb.model_dump() if hasattr(nb, "model_dump") else nb.__dict__}
        except RPCError as e:
            raise map_rpc_error(e)


@app.get("/v1/notebooks/{notebook_id}")
async def get_notebook(notebook_id: str):
    client = await get_client()
    async with client:
        try:
            nb = await client.notebooks.get(notebook_id)
            return {"ok": True, "notebook": nb.model_dump() if hasattr(nb, "model_dump") else nb.__dict__}
        except RPCError as e:
            raise map_rpc_error(e)


@app.delete("/v1/notebooks/{notebook_id}")
async def delete_notebook(notebook_id: str):
    client = await get_client()
    async with client:
        try:
            ok = await client.notebooks.delete(notebook_id)
            return {"ok": True, "deleted": bool(ok)}
        except RPCError as e:
            raise map_rpc_error(e)


@app.patch("/v1/notebooks/{notebook_id}/rename")
async def rename_notebook(notebook_id: str, req: NotebookRenameReq):
    client = await get_client()
    async with client:
        try:
            nb = await client.notebooks.rename(notebook_id, req.new_title)
            return {"ok": True, "notebook": nb.model_dump() if hasattr(nb, "model_dump") else nb.__dict__}
        except RPCError as e:
            raise map_rpc_error(e)


@app.get("/v1/notebooks/{notebook_id}/summary")
async def get_notebook_summary(notebook_id: str):
    client = await get_client()
    async with client:
        try:
            summary = await client.notebooks.get_summary(notebook_id)
            return {"ok": True, "summary": summary}
        except RPCError as e:
            raise map_rpc_error(e)


@app.get("/v1/notebooks/{notebook_id}/description")
async def get_notebook_description(notebook_id: str):
    client = await get_client()
    async with client:
        try:
            desc = await client.notebooks.get_description(notebook_id)
            return {"ok": True, "description": desc.model_dump() if hasattr(desc, "model_dump") else desc.__dict__}
        except RPCError as e:
            raise map_rpc_error(e)


# ----------------------------
# Sources
# ----------------------------
@app.get("/v1/notebooks/{notebook_id}/sources")
async def list_sources(notebook_id: str):
    client = await get_client()
    async with client:
        try:
            items = await client.sources.list(notebook_id)
            return {"ok": True, "items": [s.model_dump() if hasattr(s, "model_dump") else s.__dict__ for s in items]}
        except RPCError as e:
            raise map_rpc_error(e)


@app.post("/v1/notebooks/{notebook_id}/sources/url")
async def add_source_url(notebook_id: str, req: SourceAddUrlReq):
    client = await get_client()
    async with client:
        try:
            src = await client.sources.add_url(notebook_id, req.url, wait=req.wait)
            return {"ok": True, "source": src.model_dump() if hasattr(src, "model_dump") else src.__dict__}
        except TypeError:
            # some versions may not accept wait=; fall back
            try:
                src = await client.sources.add_url(notebook_id, req.url)
                return {"ok": True, "source": src.model_dump() if hasattr(src, "model_dump") else src.__dict__}
            except RPCError as e:
                raise map_rpc_error(e)
        except RPCError as e:
            raise map_rpc_error(e)


@app.post("/v1/notebooks/{notebook_id}/sources/youtube")
async def add_source_youtube(notebook_id: str, req: SourceAddYoutubeReq):
    client = await get_client()
    async with client:
        try:
            src = await client.sources.add_youtube(notebook_id, req.url, wait=req.wait)
            return {"ok": True, "source": src.model_dump() if hasattr(src, "model_dump") else src.__dict__}
        except TypeError:
            try:
                src = await client.sources.add_youtube(notebook_id, req.url)
                return {"ok": True, "source": src.model_dump() if hasattr(src, "model_dump") else src.__dict__}
            except RPCError as e:
                raise map_rpc_error(e)
        except RPCError as e:
            raise map_rpc_error(e)


@app.post("/v1/notebooks/{notebook_id}/sources/text")
async def add_source_text(notebook_id: str, req: SourceAddTextReq):
    client = await get_client()
    async with client:
        try:
            src = await client.sources.add_text(notebook_id, req.title, req.content)
            return {"ok": True, "source": src.model_dump() if hasattr(src, "model_dump") else src.__dict__}
        except RPCError as e:
            raise map_rpc_error(e)


@app.post("/v1/notebooks/{notebook_id}/sources/file")
async def add_source_file(
    notebook_id: str,
    upload: UploadFile = File(...),
    mime_type: Optional[str] = Form(None),
):
    # Save to temp file first
    suffix = os.path.splitext(upload.filename or "")[1] or ".bin"
    tmp_path = os.path.join(tempfile.gettempdir(), f"nb_{uuid.uuid4().hex}{suffix}")
    with open(tmp_path, "wb") as f:
        f.write(await upload.read())

    client = await get_client()
    async with client:
        try:
            src = await client.sources.add_file(notebook_id, tmp_path, mime_type=mime_type)
            return {"ok": True, "source": src.model_dump() if hasattr(src, "model_dump") else src.__dict__}
        except RPCError as e:
            raise map_rpc_error(e)
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass


@app.get("/v1/notebooks/{notebook_id}/sources/{source_id}/fulltext")
async def get_source_fulltext(notebook_id: str, source_id: str):
    client = await get_client()
    async with client:
        try:
            ft = await client.sources.get_fulltext(notebook_id, source_id)
            return {"ok": True, "fulltext": ft.model_dump() if hasattr(ft, "model_dump") else ft.__dict__}
        except RPCError as e:
            raise map_rpc_error(e)


@app.get("/v1/notebooks/{notebook_id}/sources/{source_id}/guide")
async def get_source_guide(notebook_id: str, source_id: str):
    client = await get_client()
    async with client:
        try:
            guide = await client.sources.get_guide(notebook_id, source_id)
            return {"ok": True, "guide": guide}
        except RPCError as e:
            raise map_rpc_error(e)


@app.delete("/v1/notebooks/{notebook_id}/sources/{source_id}")
async def delete_source(notebook_id: str, source_id: str):
    client = await get_client()
    async with client:
        try:
            ok = await client.sources.delete(notebook_id, source_id)
            return {"ok": True, "deleted": bool(ok)}
        except RPCError as e:
            raise map_rpc_error(e)


# ----------------------------
# Chat
# ----------------------------
@app.post("/v1/notebooks/{notebook_id}/chat/ask")
async def chat_ask(notebook_id: str, req: ChatAskReq):
    client = await get_client()
    async with client:
        try:
            result = await client.chat.ask(notebook_id, req.question)
            # result.answer is shown in docs :contentReference[oaicite:5]{index=5}
            if hasattr(result, "model_dump"):
                return {"ok": True, "result": result.model_dump()}
            return {"ok": True, "result": getattr(result, "__dict__", {"answer": getattr(result, "answer", None)})}
        except RPCError as e:
            raise map_rpc_error(e)


# ----------------------------
# Artifacts: list / generate / poll / download
# ----------------------------
@app.get("/v1/notebooks/{notebook_id}/artifacts")
async def list_artifacts(notebook_id: str, type: Optional[str] = None):
    client = await get_client()
    async with client:
        try:
            items = await client.artifacts.list(notebook_id, type=type) if type else await client.artifacts.list(notebook_id)
            return {"ok": True, "items": [a.model_dump() if hasattr(a, "model_dump") else a.__dict__ for a in items]}
        except RPCError as e:
            raise map_rpc_error(e)


@app.post("/v1/notebooks/{notebook_id}/artifacts/generate")
async def generate_artifact(notebook_id: str, req: ArtifactGenerateReq):
    client = await get_client()
    async with client:
        try:
            t = req.type
            opts = req.options or {}

            if t == "audio":
                status = await client.artifacts.generate_audio(notebook_id, **opts)
            elif t == "video":
                status = await client.artifacts.generate_video(notebook_id, **opts)
            elif t == "report":
                status = await client.artifacts.generate_report(notebook_id, **opts)
            elif t == "quiz":
                status = await client.artifacts.generate_quiz(notebook_id, **opts)
            elif t == "flashcards":
                status = await client.artifacts.generate_flashcards(notebook_id, **opts)
            elif t == "slide_deck":
                status = await client.artifacts.generate_slide_deck(notebook_id, **opts)
            elif t == "infographic":
                status = await client.artifacts.generate_infographic(notebook_id, **opts)
            elif t == "data_table":
                status = await client.artifacts.generate_data_table(notebook_id, **opts)
            elif t == "mind_map":
                # mind_map may return dict directly in docs :contentReference[oaicite:6]{index=6}
                out = await client.artifacts.generate_mind_map(notebook_id, **opts)
                return {"ok": True, "type": t, "result": out}
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported artifact type: {t}")

            # GenerationStatus commonly contains task_id :contentReference[oaicite:7]{index=7}
            payload = status.model_dump() if hasattr(status, "model_dump") else getattr(status, "__dict__", {})
            return {"ok": True, "type": t, "status": payload}
        except RPCError as e:
            raise map_rpc_error(e)


@app.get("/v1/notebooks/{notebook_id}/artifacts/tasks/{task_id}")
async def poll_task(notebook_id: str, task_id: str, wait: bool = False):
    client = await get_client()
    async with client:
        try:
            if wait:
                status = await client.artifacts.wait_for_completion(notebook_id, task_id)
            else:
                status = await client.artifacts.poll_status(notebook_id, task_id)

            payload = status.model_dump() if hasattr(status, "model_dump") else getattr(status, "__dict__", status)
            return {"ok": True, "status": payload}
        except RPCError as e:
            raise map_rpc_error(e)


@app.get("/v1/notebooks/{notebook_id}/artifacts/download")
async def download_artifact(
    notebook_id: str,
    type: Literal[
        "audio",
        "video",
        "infographic",
        "slide_deck",
        "report",
        "mind_map",
        "data_table",
        "quiz",
        "flashcards",
    ],
    artifact_id: Optional[str] = None,
    output_format: Optional[Literal["json", "markdown", "html"]] = None,
):
    """
    Downloads the *first completed* artifact of the given type unless artifact_id is provided.
    notebooklm-py provides type-specific download_* methods. :contentReference[oaicite:8]{index=8}
    """
    suffix_map = {
        "audio": ".mp4",
        "video": ".mp4",
        "infographic": ".png",
        "slide_deck": ".pdf",
        "report": ".md",
        "mind_map": ".json",
        "data_table": ".csv",
        "quiz": ".json" if (output_format in (None, "json")) else (".md" if output_format == "markdown" else ".html"),
        "flashcards": ".json" if (output_format in (None, "json")) else (".md" if output_format == "markdown" else ".html"),
    }
    out_path = os.path.join(tempfile.gettempdir(), f"nlm_{uuid.uuid4().hex}{suffix_map[type]}")

    client = await get_client()
    async with client:
        try:
            if type == "audio":
                await client.artifacts.download_audio(notebook_id, out_path, artifact_id=artifact_id)
            elif type == "video":
                await client.artifacts.download_video(notebook_id, out_path, artifact_id=artifact_id)
            elif type == "infographic":
                await client.artifacts.download_infographic(notebook_id, out_path, artifact_id=artifact_id)
            elif type == "slide_deck":
                await client.artifacts.download_slide_deck(notebook_id, out_path, artifact_id=artifact_id)
            elif type == "report":
                await client.artifacts.download_report(notebook_id, out_path, artifact_id=artifact_id)
            elif type == "mind_map":
                await client.artifacts.download_mind_map(notebook_id, out_path, artifact_id=artifact_id)
            elif type == "data_table":
                await client.artifacts.download_data_table(notebook_id, out_path, artifact_id=artifact_id)
            elif type == "quiz":
                await client.artifacts.download_quiz(
                    notebook_id, out_path, artifact_id=artifact_id, output_format=(output_format or "json")
                )
            elif type == "flashcards":
                await client.artifacts.download_flashcards(
                    notebook_id, out_path, artifact_id=artifact_id, output_format=(output_format or "json")
                )
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported type: {type}")

            filename = os.path.basename(out_path)
            return FileResponse(out_path, filename=filename)
        except RPCError as e:
            # Clean up file if partially created
            try:
                if os.path.exists(out_path):
                    os.remove(out_path)
            except OSError:
                pass
            raise map_rpc_error(e)
