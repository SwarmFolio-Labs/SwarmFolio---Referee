"""
The public deployment (Dockerfile / render.yaml) must never be able to call an LLM:
api.py may only load the Referee (pure math), and the API's requirements contain no LLM packages.
"""

import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# google.protobuf is fine (a solver dependency); google.genai / google.generativeai are LLM clients.
LLM_MODULES = ("committee", "agents", "langchain", "openai", "anthropic", "google.genai",
               "google.generativeai", "uagents", "stripe", "fakes")


def test_api_imports_no_llm_or_agent_code():
    """Importing api.py (what uvicorn does) loads none of the LLM, agent or payment modules."""
    code = ("import sys, api\n"
            f"bad = sorted(m for m in sys.modules if any(m == p or m.startswith(p + '.') or m.startswith(p + '_')"
            f" for p in {LLM_MODULES!r}))\n"
            "print(','.join(bad))")
    out = subprocess.run([sys.executable, "-c", code], cwd=REPO, capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "", f"api.py pulled in: {out.stdout.strip()}"


def test_api_requirements_have_no_llm_packages():
    """requirements-api.txt (what the Docker image installs) has the solver but no LLM/agent packages."""
    with open(os.path.join(REPO, "requirements-api.txt")) as f:
        pkgs = {line.split("#")[0].strip().lower() for line in f} - {""}
    assert {"cvxpy", "pyscipopt", "fastapi", "uvicorn"} <= pkgs
    assert not any(p.startswith(("langchain", "openai", "anthropic", "google-genai", "google-generativeai",
                                  "uagents", "stripe")) for p in pkgs)


def test_docker_image_only_copies_api_files():
    """The Dockerfile copies the API and the Referee, never committee/, agents/ or .env."""
    with open(os.path.join(REPO, "Dockerfile")) as f:
        copies = [line for line in f if line.startswith("COPY")]
    text = "".join(copies)
    assert "referee/" in text and "api.py" in text
    for forbidden in ("committee", "agents", ".env", "COPY . "):
        assert forbidden not in text
