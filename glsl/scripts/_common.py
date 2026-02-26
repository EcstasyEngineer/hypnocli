"""
_common.py
----------
Shared utilities for the GLSL shader pipeline scripts.
"""

import json
import os
import sys
import uuid
from pathlib import Path

GLSL_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = GLSL_DIR.parent
ONTOLOGY_PATH = GLSL_DIR / "ontology.json"
RATINGS_PATH = GLSL_DIR / "ratings.jsonl"
SHADERS_DIR = GLSL_DIR / "shaders"
RENDERS_DIR = GLSL_DIR / "renders"
SEEDS_DIR = GLSL_DIR / "seeds"


# ── API Key ──────────────────────────────────────────────────────────────────

def get_api_key() -> str:
    """Load ANTHROPIC_API_KEY from environment or repo-root .env."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key

    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("ANTHROPIC_API_KEY="):
                return line.split("=", 1)[1].strip()

    print("ERROR: ANTHROPIC_API_KEY not set. Add it to .env or environment.", file=sys.stderr)
    sys.exit(1)


# ── Ontology ─────────────────────────────────────────────────────────────────

def load_ontology() -> dict:
    if not ONTOLOGY_PATH.exists():
        print(f"ERROR: ontology.json not found. Run: python3 glsl/scripts/init_ontology.py", file=sys.stderr)
        sys.exit(1)
    return json.loads(ONTOLOGY_PATH.read_text())


def save_ontology(ontology: dict):
    ONTOLOGY_PATH.write_text(json.dumps(ontology, indent=2))


def nodes_active(ontology: dict, type_: str) -> list[dict]:
    return [n for n in ontology["nodes"] if n["type"] == type_ and n.get("active") and not n.get("retired")]


def node_by_id(ontology: dict, id_: str) -> dict | None:
    for n in ontology["nodes"]:
        if n["id"] == id_:
            return n
    return None


# ── Shader IDs ────────────────────────────────────────────────────────────────

def new_shader_id() -> str:
    return uuid.uuid4().hex[:12]


# ── Ratings ───────────────────────────────────────────────────────────────────

def append_rating(rating: dict):
    RATINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RATINGS_PATH, "a") as f:
        f.write(json.dumps(rating) + "\n")
