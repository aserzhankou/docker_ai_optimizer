from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import requests
import re


class OptimizeRequest(BaseModel):
    dockerfile: str


class OptimizeResponse(BaseModel):
    result: str
    summary: str


app = FastAPI(title="Dockerfile Optimizer", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")


@app.get("/healthz")
def healthcheck() -> dict:
    return {"status": "ok"}


@app.post("/api/optimize", response_model=OptimizeResponse)
def optimize(req: OptimizeRequest) -> OptimizeResponse:
    if not req.dockerfile or req.dockerfile.strip() == "":
        raise HTTPException(status_code=400, detail="dockerfile is required")

    api_key = os.getenv("ABACUS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ABACUS_API_KEY is not set")

    # Model may be configurable; default to gpt-5 to mirror your examples
    model = os.getenv("ABACUS_MODEL", "gpt-5-mini")

    system_prompt = (
        "You are an expert DevOps assistant specialized in Dockerfile optimization. "
        "Return your response in exactly this format:\n\n"
        "```dockerfile\n[OPTIMIZED_DOCKERFILE_CONTENT]\n```\n\n"
        "---SUMMARY---\n"
        "[Brief summary of changes and optimizations made]\n\n"
        "Do not include any other text or explanations outside these sections."
    )

    user_prompt = f"""
Optimize the following Dockerfile for better performance, less layers, smaller image size, and faster build time.

Don't make any changes to the Dockerfile that are not necessary for optimization.

Original Dockerfile:

```
{req.dockerfile}
```
"""

    url = "https://routellm.abacus.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "temperature": 0.2,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        data = resp.json()
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=502, detail=f"Abacus request failed: {exc}")

    content = ""
    try:
        choices = data.get("choices", []) if isinstance(data, dict) else []
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content", "")
    except Exception:
        content = ""

    if not content:
        raise HTTPException(status_code=502, detail="Empty response from Abacus ChatLLM")

    # Extract Dockerfile and summary from response
    dockerfile_content = ""
    summary_content = ""
    
    try:
        # Split by summary separator
        parts = content.split("---SUMMARY---", 1)
        if len(parts) == 2:
            dockerfile_section = parts[0].strip()
            summary_content = parts[1].strip()
            
            # Extract Dockerfile from fenced code block
            match = re.search(r"```(?:dockerfile)?\s*([\s\S]*?)```", dockerfile_section, re.IGNORECASE)
            if match:
                dockerfile_content = match.group(1).strip()
            else:
                # Fallback: extract from first FROM line
                lines = dockerfile_section.splitlines()
                start_idx = next((i for i, ln in enumerate(lines) if ln.strip().upper().startswith("FROM ")), None)
                if start_idx is not None:
                    dockerfile_content = "\n".join(lines[start_idx:]).strip()
        else:
            # Fallback: try to extract just Dockerfile
            match = re.search(r"```(?:dockerfile)?\s*([\s\S]*?)```", content, re.IGNORECASE)
            if match:
                dockerfile_content = match.group(1).strip()
            else:
                lines = content.splitlines()
                start_idx = next((i for i, ln in enumerate(lines) if ln.strip().upper().startswith("FROM ")), None)
                if start_idx is not None:
                    dockerfile_content = "\n".join(lines[start_idx:]).strip()
    except Exception:
        dockerfile_content = content  # fallback to full content

    return OptimizeResponse(result=dockerfile_content, summary=summary_content)


@app.get("/index.html")
def index_html() -> FileResponse:  # type: ignore[override]
    return FileResponse(os.path.join(static_dir, "index.html"))


# Mount static at the end to avoid intercepting API routes
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


