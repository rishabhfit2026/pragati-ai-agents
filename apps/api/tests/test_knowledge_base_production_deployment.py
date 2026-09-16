"""Regression tests for the production bug: the repo-level knowledge/
directory (app/knowledge/loader.py's data source) never reached the Render
Docker image, because apps/api/Dockerfile's build context was apps/api
itself — a sibling of knowledge/, not a parent of it — so `COPY . .` could
never see it. load_knowledge_base() doesn't error on a missing directory
(see loader.py), so every deployed analysis silently got an empty knowledge
base: Capability Matching returned UNKNOWN "No knowledge base entries
provided" for every requirement, and the Compliance Matrix came back empty.

The fix changes the Dockerfile to expect a repo-root build context (so it
can `COPY knowledge /knowledge`) instead of an apps/api-rooted one. That's a
build-context change, not something a plain pytest run can exercise through
Python imports alone — the two tiers below are:
  1. A portable check that the real repo-root knowledge/ directory (the
     exact thing `COPY knowledge /knowledge` copies) is present and, when
     pointed to via KNOWLEDGE_DIR exactly as production will have it,
     load_knowledge_base() returns real, non-empty data.
  2. An actual `docker build` of the fixed Dockerfile from the repo root,
     run only when a Docker daemon is reachable, proving the fix works in
     the same build mechanism Render uses.
"""
from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
REPO_KNOWLEDGE_DIR = os.path.join(REPO_ROOT, "knowledge")
DOCKERFILE = os.path.join(REPO_ROOT, "apps", "api", "Dockerfile")


def test_repo_root_knowledge_directory_is_exactly_what_the_dockerfile_copies():
    """Sanity-anchor: if this ever stops being true, the Dockerfile's
    `COPY knowledge /knowledge` (context = repo root) would be copying the
    wrong thing or nothing at all."""
    assert os.path.isdir(REPO_KNOWLEDGE_DIR), (
        f"Expected a knowledge/ directory at the repo root ({REPO_KNOWLEDGE_DIR}) — "
        "this is exactly the path apps/api/Dockerfile's `COPY knowledge /knowledge` "
        "expects when built with the repo root as its build context."
    )
    assert os.path.isfile(os.path.join(REPO_KNOWLEDGE_DIR, "company.json"))
    assert os.path.isdir(os.path.join(REPO_KNOWLEDGE_DIR, "products"))
    assert os.path.isdir(os.path.join(REPO_KNOWLEDGE_DIR, "capabilities"))

    from pathlib import Path

    assert list(Path(REPO_KNOWLEDGE_DIR, "products").glob("*.json")), (
        "products/ must contain at least one *.json file or capability matching has nothing to match against"
    )


def test_load_knowledge_base_from_the_real_production_knowledge_directory_returns_real_data(monkeypatch):
    """Points KNOWLEDGE_DIR at the actual repo-root knowledge/ directory —
    the same directory the Dockerfile now bakes into the image at /knowledge
    — and proves load_knowledge_base() returns real products, capabilities,
    and company data, not the silent-empty fallback that caused the
    production bug (UNKNOWN "No knowledge base entries provided" for every
    requirement)."""
    monkeypatch.setenv("KNOWLEDGE_DIR", REPO_KNOWLEDGE_DIR)

    import app.config as config_module
    importlib.reload(config_module)
    assert str(config_module.KNOWLEDGE_DIR) == REPO_KNOWLEDGE_DIR

    import app.knowledge.loader as loader_module
    importlib.reload(loader_module)  # also clears the @lru_cache on load_knowledge_base
    kb = loader_module.load_knowledge_base()

    assert kb["products"], "products list is empty — this is exactly the production bug's symptom"
    assert kb["capabilities"], "capabilities dict is empty — Compliance Agent would have nothing to check against"
    assert kb["company"], "company dict is empty — company-fact-based compliance checks would have nothing to cite"

    # A concrete, non-generic check that this is real Pragati data, not an
    # accidental non-empty-but-meaningless structure.
    product_ids = {p["id"] for p in kb["products"] if "id" in p}
    assert product_ids, "products were loaded but none have an 'id' — capability_matching.py cites this field"

    importlib.reload(config_module)  # restore for any test that runs after this one


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        subprocess.run(["docker", "info"], capture_output=True, timeout=10, check=True)
        return True
    except Exception:
        return False


requires_docker = pytest.mark.skipif(
    not _docker_available(),
    reason="No reachable Docker daemon — this test builds and runs the actual production "
           "Dockerfile to prove the fix end-to-end, the same way Render would.",
)


@requires_docker
def test_dockerfile_builds_with_repo_root_context_and_bakes_in_a_working_knowledge_base():
    """The real end-to-end proof: build apps/api/Dockerfile exactly the way
    Render must be configured to build it (Dockerfile Path=apps/api/Dockerfile,
    Docker Build Context Directory=repo root), then run the resulting image
    with no volume mounts at all (Render has none) and confirm /knowledge is
    populated and load_knowledge_base() returns real data from inside the
    container — not just from the host filesystem."""
    image_tag = "pragati-api-knowledge-fix-test:pytest"

    build = subprocess.run(
        ["docker", "build", "-f", DOCKERFILE, "-t", image_tag, REPO_ROOT],
        capture_output=True, text=True, timeout=600,
    )
    assert build.returncode == 0, f"docker build failed:\nSTDOUT:\n{build.stdout}\nSTDERR:\n{build.stderr}"

    try:
        run = subprocess.run(
            [
                "docker", "run", "--rm", image_tag,
                "python", "-c",
                "import json, os; "
                "from app.knowledge.loader import load_knowledge_base; "
                "kb = load_knowledge_base(); "
                "assert os.environ.get('KNOWLEDGE_DIR') == '/knowledge', os.environ.get('KNOWLEDGE_DIR'); "
                "assert os.path.isdir('/knowledge'), '/knowledge missing inside the image'; "
                "assert kb['products'], 'no products loaded inside the container'; "
                "assert kb['capabilities'], 'no capabilities loaded inside the container'; "
                "assert kb['company'], 'no company data loaded inside the container'; "
                "print(json.dumps({'products': len(kb['products']), "
                "'capabilities': list(kb['capabilities'].keys()), "
                "'company_keys': list(kb['company'].keys())}))",
            ],
            capture_output=True, text=True, timeout=60,
        )
        assert run.returncode == 0, f"container check failed:\nSTDOUT:\n{run.stdout}\nSTDERR:\n{run.stderr}"
        payload = json.loads(run.stdout.strip().splitlines()[-1])
        assert payload["products"] > 0
        assert payload["capabilities"]
        assert payload["company_keys"]
    finally:
        subprocess.run(["docker", "rmi", "-f", image_tag], capture_output=True)
