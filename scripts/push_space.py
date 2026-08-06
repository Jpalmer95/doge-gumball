#!/usr/bin/env python3
"""Deploy the machine to a Hugging Face Space (sdk: docker).

Assembles the Space repo (entry point + Dockerfile + app package + frontend
+ docs) and pushes it, then sets the HF_TOKEN and DOGE_ADDRESS secrets and
polls the build until the Space is RUNNING (or fails loudly).

Usage:
    SPACE_REPO=jkorstad/doge-gumball python3 scripts/push_space.py
    DOGE_ADDRESS=<real address> SPACE_REPO=... python3 scripts/push_space.py

Notes:
  * HF token is read from HF_TOKEN env or ~/.cache/huggingface/token.
  * sdk: docker + cpu-basic gives a plain FastAPI container — no Gradio
    runtime quirks (gr.HTML script stripping, launcher route wiping,
    port-7860 conflicts).
  * Existing Space is reused (idempotent); file uploads commit on top.
"""
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPACE_REPO = os.environ.get("SPACE_REPO", "jkorstad/doge-gumball")
SPACE_HARDWARE = os.environ.get("SPACE_HARDWARE", "cpu-basic")
SPACE_SDK = os.environ.get("SPACE_SDK", "docker")


def resolve_token() -> str:
    for key in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        if os.environ.get(key):
            return os.environ[key].strip()
    cache = Path.home() / ".cache" / "huggingface" / "token"
    if cache.exists():
        tok = cache.read_text().strip()
        if tok:
            return tok
    raise SystemExit("HF token not found (HF_TOKEN env or ~/.cache/huggingface/token)")


def assemble(tmp: Path) -> None:
    """Copy the pieces the Space needs into a clean staging dir."""
    shutil.copy(ROOT / "space" / "space_app.py", tmp / "space_app.py")
    shutil.copy(ROOT / "space" / "Dockerfile", tmp / "Dockerfile")
    shutil.copy(ROOT / "space" / "README.md", tmp / "README.md")
    shutil.copy(ROOT / "space" / "requirements.txt", tmp / "requirements.txt")
    shutil.copytree(ROOT / "app", tmp / "app",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(ROOT / "frontend", tmp / "frontend",
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "docs", tmp / "docs")


def main() -> int:
    from huggingface_hub import HfApi, create_repo

    token = resolve_token()
    api = HfApi(token=token)

    print(f"[1/4] ensuring Space {SPACE_REPO} (sdk={SPACE_SDK}, hardware={SPACE_HARDWARE})")
    create_repo(
        repo_id=SPACE_REPO, repo_type="space", space_sdk=SPACE_SDK,
        space_hardware=SPACE_HARDWARE, token=token, exist_ok=True,
    )

    print("[2/4] uploading files (per-file, retryable)")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        assemble(tmp)
        files = sorted(str(p.relative_to(tmp)) for p in tmp.rglob("*") if p.is_file())
        for rel in files:
            for attempt in range(4):
                try:
                    api.upload_file(
                        path_or_fileobj=str(tmp / rel), path_in_repo=rel,
                        repo_id=SPACE_REPO, repo_type="space", token=token,
                        commit_message=f"deploy: {rel}",
                    )
                    break
                except Exception as e:
                    if attempt == 3:
                        print(f"❌ failed to upload {rel}: {e}")
                        return 1
                    time.sleep(5 * (attempt + 1))
        print(f"      {len(files)} files uploaded")

    print("[3/4] setting secrets")
    api.add_space_secret(repo_id=SPACE_REPO, key="HF_TOKEN", value=token)
    doge = os.environ.get("DOGE_ADDRESS")
    if doge:
        api.add_space_secret(repo_id=SPACE_REPO, key="DOGE_ADDRESS", value=doge)
        print("      DOGE_ADDRESS secret set")
    else:
        print("      (no DOGE_ADDRESS env — machine will report the placeholder; "
              "set the real address via Space secrets when the wallet exists)")

    print("[4/4] polling build (stage: PENDING -> BUILDING -> RUNNING)")
    for i in range(90):  # docker builds can take a while: up to 15 minutes
        info = api.space_info(SPACE_REPO, expand=["runtime"])
        stage = (info.runtime or {}).stage if info.runtime else "PENDING"
        print(f"      ...{stage}")
        if stage == "RUNNING":
            print(f"✅ Space live: https://huggingface.co/spaces/{SPACE_REPO}")
            return 0
        if stage in ("CONFIG_ERROR", "RUNTIME_ERROR", "ERROR"):
            raw = (info.runtime or {}).raw or {}
            print(f"❌ build failed: {raw.get('errorMessage', 'unknown error')}")
            return 1
        time.sleep(10)
    print("❌ timed out waiting for the build")
    return 1


if __name__ == "__main__":
    sys.exit(main())
