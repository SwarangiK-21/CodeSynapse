"""Uploads this repository to a Hugging Face Space.

Run by .github/workflows/deploy.yml after CI passes on main. It needs:
  HF_SPACE          the Space id, for example SwarangiK-21/CodeSynapse
  and one way to sign in:
  HF_OIDC_RESOURCE  spaces/<HF_SPACE>, set in CI. GitHub proves its identity to Hugging Face
                    (a "trusted publisher" on the Space) and gets a one-hour token, so no
                    token is stored anywhere.
  HF_TOKEN          or a Hugging Face token with write access, for running it by hand

Spaces read their settings from the README's front matter, so the uploaded README
gets that header added. The GitHub README stays unchanged.
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path
from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parent.parent

# Only what the container needs; evals, tests and docs stay on GitHub
INCLUDE = ["app.py", "Dockerfile", "requirements.txt", "alembic.ini", "codesynapse", "migrations", "docs/images"]

FRONT_MATTER = """---
title: CodeSynapse
emoji: 🧠
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
short_description: Skill-gap agent that cites real code as evidence
---

"""

def build(target):
    for name in INCLUDE:
        source = ROOT / name
        if source.is_dir():
            shutil.copytree(source, target / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(source, target / name)
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    (target / "README.md").write_text(FRONT_MATTER + readme, encoding="utf-8")

def main():
    space = os.getenv("HF_SPACE")
    if not space or not (os.getenv("HF_OIDC_RESOURCE") or os.getenv("HF_TOKEN")):
        sys.exit("Set HF_SPACE, and HF_OIDC_RESOURCE (in CI) or HF_TOKEN.")
    with tempfile.TemporaryDirectory() as folder:
        target = Path(folder)
        build(target)
        # With no token given, huggingface_hub uses HF_OIDC_RESOURCE, then HF_TOKEN
        HfApi().upload_folder(
            repo_id=space, repo_type="space", folder_path=target,
            # Removes files from older versions of the Space that are no longer uploaded
            delete_patterns="*",
            commit_message=f"Deploy {os.getenv('GITHUB_SHA', 'local')[:7]} from GitHub",
        )
    print(f"Uploaded to https://huggingface.co/spaces/{space}")

if __name__ == "__main__":
    main()
