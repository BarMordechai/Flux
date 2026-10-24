"""Deploy the processing server to a Hugging Face Space (Docker). Used by .github/workflows/deploy-space.yml.

Env: HF_TOKEN (write token), FLUENCY_API_KEY (shared with the app), SPACE_NAME (default "shetef").
Prints the server URL.
"""

import os
import shutil
import tempfile
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parent.parent


def main():
    api = HfApi(token=os.environ["HF_TOKEN"])
    user = api.whoami()["name"]
    repo = f"{user}/{os.environ.get('SPACE_NAME', 'shetef')}"
    api.create_repo(repo, repo_type="space", space_sdk="docker", exist_ok=True)
    if os.environ.get("FLUENCY_API_KEY"):
        api.add_space_secret(repo, "FLUENCY_API_KEY", os.environ["FLUENCY_API_KEY"])
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        for f in ("Dockerfile", "README.md"):
            shutil.copy(ROOT / "space" / f, t / f)
        shutil.copy(ROOT / "requirements.txt", t / "requirements.txt")
        shutil.copytree(ROOT / "fluency", t / "fluency", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(ROOT / "web", t / "web")
        api.upload_folder(folder_path=tmp, repo_id=repo, repo_type="space", commit_message="Deploy from GitHub")
    print(f"https://{repo.replace('/', '-').replace('_', '-').lower()}.hf.space")


if __name__ == "__main__":
    main()
