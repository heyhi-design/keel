"""
Shared pytest setup: import the registry module and build the fixture registries the
test modules search against.

The module under test is `skills/registry/skill-registry.py`. Its filename is
hyphenated, so it cannot be imported by name (`import skill-registry` is a syntax
error) and has to be loaded from its path.

Every capability in every fixture below is invented for these tests. None of them
describe a real firm's skills, and the fixtures deliberately use different weights and
shapes from the two examples shipped in skill-registry.template.yaml, so a test passing
here says something about the search code rather than about the shipped examples.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / "skills" / "registry" / "skill-registry.py"
TEMPLATE_REGISTRY = REPO_ROOT / "skills" / "registry" / "skill-registry.template.yaml"

__all__ = ["REPO_ROOT", "MODULE_PATH", "TEMPLATE_REGISTRY", "sr"]


def _load_registry_module():
    spec = importlib.util.spec_from_file_location("skill_registry", MODULE_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover - only if the file moves
        raise ImportError(f"Could not load the registry module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)

    # Register the module in sys.modules BEFORE exec_module(). The module declares
    # `from __future__ import annotations`, which defers its dataclass field types to
    # strings; the dataclass machinery resolves them by looking the module up in
    # sys.modules at class-creation time. Exec first and that lookup finds nothing, and
    # the import dies with a bare "AttributeError: 'NoneType' object has no attribute
    # '__dict__'" that points nowhere near the real cause.
    sys.modules["skill_registry"] = module
    spec.loader.exec_module(module)
    return module


sr = _load_registry_module()


@pytest.fixture
def registry_module():
    """The module under test."""
    return sr


def _cap(**kwargs):
    """Build a Capability with sensible defaults, overriding only what a test cares about."""
    defaults = {
        "id": "sample-capability",
        "name": "Sample Capability",
        "type": "skill",
        "description": "",
        "semantic_tags": [],
        "trigger_patterns": [],
        "dependencies": [],
        "not_for": [],
        "load_cost_tokens": 1000,
        "location": "skills/templates/sample/SKILL.md",
    }
    defaults.update(kwargs)
    return sr.Capability(**defaults)


@pytest.fixture
def cap_factory():
    """A Capability builder, for tests that need to isolate one scoring signal at a time."""
    return _cap


@pytest.fixture
def sample_registry():
    """
    A small invented registry with a deliberate disambiguation pair.

    `invoice-drafter` and `invoice-auditor` overlap heavily on domain vocabulary
    ("invoice", "billing") and are separated only by their not_for clauses and their
    action verbs. That pair is what makes the not_for tests mean something: without the
    negative scoring, a "review the invoice for errors" query is genuinely ambiguous
    between them.
    """
    return [
        _cap(
            id="invoice-drafter",
            name="Invoice Drafter",
            type="skill",
            description="Draft a new client invoice from a statement of work and a log of hours worked.",
            semantic_tags=["invoicing", "billing", "client paperwork"],
            trigger_patterns=["draft an invoice", "create an invoice", "bill the client"],
            not_for=[
                "Reviewing an invoice that already exists (use invoice-auditor)",
                "Chasing an overdue payment (use payment-chaser)",
            ],
            load_cost_tokens=1200,
            location="skills/templates/invoice-drafter/SKILL.md",
        ),
        _cap(
            id="invoice-auditor",
            name="Invoice Auditor",
            type="skill",
            description="Review an existing invoice for arithmetic errors, missing line items, and wrong rates.",
            semantic_tags=["invoicing", "billing", "quality check"],
            trigger_patterns=["review an invoice", "check the invoice", "audit the invoice"],
            not_for=["Drafting a brand new invoice from scratch (use invoice-drafter)"],
            load_cost_tokens=900,
            location="skills/templates/invoice-auditor/SKILL.md",
        ),
        _cap(
            id="greenhouse-planner",
            name="Greenhouse Planner",
            type="reference",
            description="Plan a seasonal planting schedule for a small greenhouse, by crop and by bed.",
            semantic_tags=["gardening", "seasonal planning"],
            trigger_patterns=["plan the greenhouse", "planting schedule"],
            load_cost_tokens=4000,
            location="reference/greenhouse.md",
        ),
    ]


# ── helpers for the few-person tools (os/*.py, keelson/*.py) ────────────────
#
# The tools are scripts, not a package, so each is loaded from its path. The git helper runs
# with a fixed identity and no signing, and without the developer's global or system git
# config, so a scratch repository behaves the same on every machine and in CI.

import os
import subprocess


def load_tool(relative, name):
    """Load a keel tool script (e.g. "os/resolve_operator.py") as a module."""
    path = REPO_ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def git_env(tmp_root):
    env = dict(os.environ)
    empty = Path(tmp_root) / ".gitconfig-empty"
    empty.write_text("", encoding="utf-8")
    env.update(
        GIT_CONFIG_GLOBAL=str(empty),
        GIT_CONFIG_NOSYSTEM="1",
        GIT_AUTHOR_NAME="Test Operator",
        GIT_AUTHOR_EMAIL="test-operator@example.com",
        GIT_COMMITTER_NAME="Test Operator",
        GIT_COMMITTER_EMAIL="test-operator@example.com",
        GIT_TERMINAL_PROMPT="0",
    )
    return env


class Repo:
    """A scratch git repository for the tool tests."""

    def __init__(self, path, env):
        self.path = Path(path)
        self.env = env

    def git(self, *args, cwd=None, check=True):
        out = subprocess.run(
            ["git", "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false", *args],
            cwd=str(cwd or self.path), env=self.env, capture_output=True, text=True,
        )
        if check and out.returncode != 0:
            raise AssertionError(f"git {' '.join(args)} failed: {out.stderr}")
        return out.stdout.strip()

    def write(self, rel, text):
        target = self.path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def commit(self, message="change"):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")


@pytest.fixture
def scratch_repo(tmp_path, monkeypatch):
    """An empty repository on `main` with one commit, isolated from the machine's git config."""
    env = git_env(tmp_path)
    for key in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM"):
        monkeypatch.setenv(key, env[key])
    root = tmp_path / "instance"
    root.mkdir()
    repo = Repo(root, env)
    repo.git("init", "-q", "-b", "main")
    repo.write("README.md", "# scratch instance\n")
    repo.commit("initial")
    return repo
