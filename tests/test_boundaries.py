"""Architecture-boundary enforcement.

These tests exist to keep the library from quietly growing into an agent
framework. They assert on the source tree, not on runtime behaviour.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "temporal_awareness"

#: Allowed top-level modules for absolute imports. Anything else is a
#: dependency creep and must fail the suite.
ALLOWED_IMPORT_ROOTS = {
    "__future__",
    "datetime",
    "dataclasses",
    "enum",
    "typing",
    "typing_extensions",
    "zoneinfo",
}

# Words that are fine in a docstring/prose but must never appear as an import
# or an attribute access.
FORBIDDEN_IMPORT_ROOTS = {
    "openai",
    "anthropic",
    "google",
    "ollama",
    "requests",
    "httpx",
    "numpy",
    "pandas",
    "sqlite3",
    "schedule",
    "apscheduler",
    "dateutil",
    "pytz",
}


def source_files():
    return sorted(SRC.glob("*.py"))


def parse(path: Path):
    return ast.parse(path.read_text(encoding="utf-8"))


def code_without_docstrings(path: Path) -> str:
    """Source with docstrings stripped, so prose about boundaries is not
    mistaken for boundary violations."""

    tree = parse(path)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                if isinstance(body[0].value.value, str):
                    node.body = body[1:] or [ast.Pass()]
    return ast.unparse(tree)


class TestNoForbiddenDependencies:
    def test_third_party_imports_are_absent(self):
        offenders = []
        for path in source_files():
            tree = parse(path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split(".")[0] in FORBIDDEN_IMPORT_ROOTS:
                            offenders.append(f"{path.name}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom) and node.module:
                    if node.module.split(".")[0] in FORBIDDEN_IMPORT_ROOTS:
                        offenders.append(f"{path.name}: from {node.module}")
        assert offenders == []

    def test_only_stdlib_and_internal_imports(self):
        """Allowlist check over BOTH import forms.

        `import openai` and `from openai import X` are different AST nodes.
        Checking only ImportFrom lets a plain `import openai` walk straight
        through, so both are covered here.
        """

        for path in source_files():
            for node in ast.walk(parse(path)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root = alias.name.split(".")[0]
                        assert root in ALLOWED_IMPORT_ROOTS, (
                            f"{path.name} imports unexpected module {alias.name}"
                        )
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    root = node.module.split(".")[0]
                    assert root in ALLOWED_IMPORT_ROOTS, (
                        f"{path.name} imports unexpected module {node.module}"
                    )


class TestNoCognition:
    def test_no_intent_or_emotion_inference(self):
        offenders = []
        for path in source_files():
            code = code_without_docstrings(path).lower()
            for word in (
                "infer_intent",
                "infer_emotion",
                "predict_action",
                "agent_should",
                "detect_mood",
                "classify_intent",
            ):
                if word in code:
                    offenders.append(f"{path.name}: {word}")
        assert offenders == []

    def test_no_model_calls(self):
        offenders = []
        for path in source_files():
            code = code_without_docstrings(path)
            for pattern in (
                r"\.chat\.completions",
                r"\.generate_content",
                r"requests\.",
                r"httpx\.",
                r"openai\.",
                r"anthropic\.",
            ):
                if re.search(pattern, code):
                    offenders.append(f"{path.name}: {pattern}")
        assert offenders == []

    def test_no_network_or_persistence(self):
        for path in source_files():
            code = code_without_docstrings(path)
            for pattern in (r"\bopen\(", r"\bsocket\b", r"sqlite", r"urlopen", r"pathlib", r"os\.environ"):
                assert not re.search(pattern, code), f"{path.name} uses {pattern}"


class TestNoSoulOsDependency:
    def test_no_soul_os_reference_in_source(self):
        for path in source_files():
            lowered = path.read_text(encoding="utf-8").lower()
            assert "soul_os" not in lowered
            assert "soul-os" not in lowered

    def test_no_soul_os_import(self):
        for path in source_files():
            for node in ast.walk(parse(path)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    assert "soul" not in node.module.lower()
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "soul" not in alias.name.lower()

    def test_package_has_no_config_or_data_access(self):
        # A pure library: no .env, no config files, no data directories.
        unexpected = [
            str(p.relative_to(SRC))
            for p in SRC.rglob("*")
            if p.is_file()
            and p.suffix not in {".py", ".pyi"}
            and "__pycache__" not in p.parts
        ]
        assert unexpected == []


class TestPublicSurfaceIsSmall:
    def test_exports_are_declared(self):
        init = (SRC / "__init__.py").read_text(encoding="utf-8")
        tree = ast.parse(init)
        exported = None
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                getattr(t, "id", None) == "__all__" for t in node.targets
            ):
                exported = [el.value for el in node.value.elts]
        assert exported is not None
        assert 10 <= len(exported) <= 30

    def test_every_export_exists(self):
        import temporal_awareness

        for name in temporal_awareness.__all__:
            assert hasattr(temporal_awareness, name), f"{name} is exported but missing"

    def test_version_is_set(self):
        import temporal_awareness

        assert temporal_awareness.__version__ == "0.1.0"
