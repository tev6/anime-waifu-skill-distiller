import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from services import distill, chat

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Anime Waifu Skill Distiller")

MAX_BODY_SIZE = 65536  # 64KB

BASE_DIR = Path(__file__).parent
SKILLS_DIR = BASE_DIR / ".claude" / "skills"
USER_SKILLS_DIR = Path.home() / ".claude" / "skills"


def _check_body_size(request: Request):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_SIZE:
        raise HTTPException(status_code=413, detail="Request body too large. Max 64KB.")

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

INDEX_HTML = (BASE_DIR / "templates" / "index.html").read_text(encoding="utf-8")


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(content=INDEX_HTML)


@app.post("/api/generate")
async def generate(request: Request):
    _check_body_size(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    corpus = body.get("corpus", "").strip()
    intensity = body.get("intensity", "full")
    provider = body.get("provider", "anthropic")
    api_key = body.get("api_key", "")
    model = body.get("model", "")
    base_url = body.get("base_url", "")

    if not corpus:
        raise HTTPException(status_code=400, detail="corpus is required")

    if intensity not in ("light", "full"):
        intensity = "full"

    try:
        result = distill(corpus, intensity, provider, api_key, model, base_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Configuration error: {str(e)}")
    except Exception as e:
        logger.error("LLM call failed in /api/generate: %s", e)
        raise HTTPException(status_code=500, detail="LLM call failed. Check your API key and network connection.")

    return result


@app.post("/api/chat")
async def chat_endpoint(request: Request):
    _check_body_size(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    skill_md = body.get("skill_md", "")
    message = body.get("message", "").strip()
    provider = body.get("provider", "anthropic")
    api_key = body.get("api_key", "")
    model = body.get("model", "")
    base_url = body.get("base_url", "")

    if not skill_md:
        raise HTTPException(status_code=400, detail="skill_md is required")
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    try:
        reply = chat(skill_md, message, provider, api_key, model, base_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Configuration error: {str(e)}")
    except Exception as e:
        logger.error("LLM call failed in /api/chat: %s", e)
        raise HTTPException(status_code=500, detail="Chat request failed. Check your API key and network connection.")

    return {"reply": reply}


@app.post("/api/install")
async def install(request: Request):
    _check_body_size(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    skill_md = body.get("skill_md", "")
    scope = body.get("scope", "project")  # "project" or "user"

    if not skill_md:
        raise HTTPException(status_code=400, detail="skill_md is required")

    # Extract skill name from markdown
    skill_name = "character-coding-companion"
    for line in skill_md.split("\n"):
        line = line.strip()
        if line.startswith("name:") or line.startswith("## Skill:"):
            skill_name = line.split(":", 1)[1].strip().replace(" ", "-").lower()
            if skill_name:
                break

    skill_name = "".join(c for c in skill_name if c.isalnum() or c in "-_") or "character"

    target_dir = USER_SKILLS_DIR if scope == "user" else SKILLS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    file_path = target_dir / f"{skill_name}.md"
    file_path.write_text(skill_md, encoding="utf-8")

    return {"installed": str(file_path), "name": skill_name, "scope": scope}
