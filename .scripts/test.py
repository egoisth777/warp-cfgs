"""Test and lint suite for .scripts/.

Phases:
  1. Lint   — AST-based shim enforcement + path rules
  2. Integrity — REPOS.json schema, .gitignore consistency, directory structure
  3. Regression — unittest cases for lib/ modules

Usage: python .scripts/test.py
Exit 0 = all passed, Exit 1 = any failed.
"""

import ast
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / ".scripts"


# --- Phase 1: Lint ---

BANNED_CALLS = {
    ("os", "symlink"): "use native script (.ps1/.sh) for symlink creation",
    ("os", "remove"): "use native script (.ps1/.sh) for file removal",
    ("os", "unlink"): "use native script (.ps1/.sh) for file removal",
    ("shutil", "rmtree"): "use native script (.ps1/.sh) for directory removal",
    ("os.path", "expanduser"): "~ expansion belongs in native scripts, not Python",
}

BANNED_METHODS = {
    "symlink_to": "use native script (.ps1/.sh) for symlink creation",
    "unlink": "use native script (.ps1/.sh) for file removal",
}


class ShimChecker(ast.NodeVisitor):
    """AST visitor that flags banned OS operations in Python shims."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.violations: list[str] = []

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                key = (node.func.value.id, node.func.attr)
                if key in BANNED_CALLS:
                    self.violations.append(
                        f"  {self.filepath}:{node.lineno}: "
                        f"{key[0]}.{key[1]}() — {BANNED_CALLS[key]}"
                    )
            if (isinstance(node.func.value, ast.Attribute)
                    and isinstance(node.func.value.value, ast.Name)):
                key = (
                    f"{node.func.value.value.id}.{node.func.value.attr}",
                    node.func.attr,
                )
                if key in BANNED_CALLS:
                    self.violations.append(
                        f"  {self.filepath}:{node.lineno}: "
                        f"{key[0]}.{key[1]}() — {BANNED_CALLS[key]}"
                    )
            if node.func.attr in BANNED_METHODS:
                self.violations.append(
                    f"  {self.filepath}:{node.lineno}: "
                    f".{node.func.attr}() — {BANNED_METHODS[node.func.attr]}"
                )

        if isinstance(node.func, ast.Attribute) and node.func.attr == "run":
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess":
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        self.violations.append(
                            f"  {self.filepath}:{node.lineno}: "
                            f"subprocess.run(shell=True) — call a script file, not inline shell"
                        )

        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if (isinstance(target, ast.Subscript)
                    and isinstance(target.value, ast.Attribute)
                    and isinstance(target.value.value, ast.Name)
                    and target.value.value.id == "os"
                    and target.value.attr == "environ"):
                self.violations.append(
                    f"  {self.filepath}:{node.lineno}: "
                    f"os.environ mutation — environment changes belong in native scripts"
                )
        self.generic_visit(node)


def lint_shim_enforcement(scripts_dir: Path) -> list[str]:
    """AST-walk all .py files under .scripts/ checking shim rules."""
    violations = []
    for py_file in sorted(scripts_dir.rglob("*.py")):
        if py_file.name == "test.py":
            continue
        if "__pycache__" in str(py_file):
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except SyntaxError as e:
            violations.append(f"  {py_file}: SyntaxError — {e}")
            continue
        checker = ShimChecker(str(py_file.relative_to(scripts_dir.parent)))
        checker.visit(tree)
        violations.extend(checker.violations)
    return violations


# Absolute path patterns for .py string literals
_ABS_PATH_PY = re.compile(
    r'[A-Z]:\\|/home/|/Users/|/mnt/|/tmp/|/usr/local'
)

# Absolute path patterns for .ps1/.sh
_ABS_PATH_NATIVE = re.compile(
    r'[A-Z]:\\|/home/|/Users/|/mnt/|/usr/local|/tmp/'
)

# Home dir expansion in Python
_HOME_EXPAND_PY = re.compile(r'~[/\\]|%USERPROFILE%|\$HOME')


def lint_path_rules_py(scripts_dir: Path) -> list[str]:
    """Check .py files for path violations via AST."""
    violations = []
    for py_file in sorted(scripts_dir.rglob("*.py")):
        if py_file.name == "test.py" or "__pycache__" in str(py_file):
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except SyntaxError:
            continue
        rel = str(py_file.relative_to(scripts_dir.parent))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if _ABS_PATH_PY.search(node.value):
                    violations.append(
                        f"  {rel}:{node.lineno}: hardcoded absolute path in string: {node.value!r}"
                    )
                if _HOME_EXPAND_PY.search(node.value):
                    violations.append(
                        f"  {rel}:{node.lineno}: home dir reference in string: {node.value!r}"
                    )
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                for side in (node.left, node.right):
                    if isinstance(side, ast.Constant) and isinstance(side.value, str):
                        if re.search(r'[/\\]', side.value) and side.value not in ("/", "\\"):
                            violations.append(
                                f"  {rel}:{node.lineno}: string concatenation with path separator — use Path or os.path.join"
                            )
                            break
    return violations


def lint_path_rules_native(scripts_dir: Path) -> list[str]:
    """Line-by-line regex scan of .ps1/.sh files for path violations."""
    violations = []
    for ext in ("*.ps1", "*.sh"):
        for native_file in sorted(scripts_dir.rglob(ext)):
            if "__pycache__" in str(native_file):
                continue
            rel = str(native_file.relative_to(scripts_dir.parent))
            for lineno, line in enumerate(native_file.read_text(encoding="utf-8").splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if _ABS_PATH_NATIVE.search(line):
                    violations.append(
                        f"  {rel}:{lineno}: hardcoded absolute path: {line.strip()!r}"
                    )
    return violations


# --- Phase 2: Integrity ---

REQUIRED_KEYS = {"url", "path"}


def check_repos_json(root: Path) -> list[str]:
    """Validate REPOS.json schema and constraints."""
    issues = []
    repos_file = root / "REPOS.json"

    if not repos_file.exists():
        issues.append("  REPOS.json does not exist")
        return issues

    try:
        data = json.loads(repos_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError) as e:
        issues.append(f"  REPOS.json is not valid JSON: {e}")
        return issues

    if not isinstance(data, list):
        issues.append(f"  REPOS.json must be a flat array, got {type(data).__name__}")
        return issues

    seen_paths = set()

    for i, entry in enumerate(data):
        prefix = f"  REPOS.json[{i}]"
        if not isinstance(entry, dict):
            issues.append(f"{prefix}: expected object, got {type(entry).__name__}")
            continue
        keys = set(entry.keys())
        if keys != REQUIRED_KEYS:
            missing = REQUIRED_KEYS - keys
            extra = keys - REQUIRED_KEYS
            if missing:
                issues.append(f"{prefix}: missing keys: {missing}")
            if extra:
                issues.append(f"{prefix}: unexpected keys: {extra}")
            continue
        for k in REQUIRED_KEYS:
            if not isinstance(entry[k], str):
                issues.append(f"{prefix}: '{k}' must be a string, got {type(entry[k]).__name__}")
        if "/" in entry["path"] or "\\" in entry["path"]:
            issues.append(f"{prefix}: path must be a bare name (no slashes): '{entry['path']}'")

        if entry["path"] in seen_paths:
            issues.append(f"{prefix}: duplicate path: '{entry['path']}'")
        seen_paths.add(entry["path"])

    return issues


def check_gitignore_consistency(root: Path) -> list[str]:
    """Every path in REPOS.json must appear in .gitignore."""
    issues = []
    repos_file = root / "REPOS.json"
    gitignore_file = root / ".gitignore"

    if not repos_file.exists():
        return issues

    try:
        data = json.loads(repos_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return issues
    if not isinstance(data, list):
        return issues

    if gitignore_file.exists():
        ignored = set(gitignore_file.read_text(encoding="utf-8").splitlines())
    else:
        ignored = set()

    for entry in data:
        if not isinstance(entry, dict):
            continue
        path = entry.get("path", "")
        if path and path not in ignored:
            issues.append(f"  [warn] path '{path}' in REPOS.json but not in .gitignore")

    return issues


def check_directory_structure(root: Path) -> list[str]:
    """Warn about on-disk git repos not tracked in REPOS.json."""
    issues = []
    repos_file = root / "REPOS.json"

    if not repos_file.exists():
        return issues

    try:
        data = json.loads(repos_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        issues.append("  REPOS.json is not valid JSON; skipping directory structure validation")
        return issues
    if not isinstance(data, list):
        return issues

    tracked_paths = {e["path"] for e in data if isinstance(e, dict) and "path" in e}
    skip_dirs = {".git", ".scripts", ".github", "docs"}

    for item in sorted(root.iterdir()):
        if not item.is_dir():
            continue
        if item.name in skip_dirs or item.name.startswith("."):
            continue
        if item.name in tracked_paths:
            # Check it has .git
            if not (item / ".git").exists():
                issues.append(f"  {item.name}: tracked in REPOS.json but has no .git directory")
            continue
        # Untracked directory — check if it's a git repo
        if (item / ".git").exists():
            print(f"  [warn] {item.name}: git repo on disk not tracked in REPOS.json")

    return issues


def run_lint() -> int:
    violations = []

    print("[lint] Checking .scripts/*.py shim rules...")
    violations.extend(lint_shim_enforcement(SCRIPTS))

    print("[lint] Checking path rules across .py/.ps1/.sh...")
    violations.extend(lint_path_rules_py(SCRIPTS))
    violations.extend(lint_path_rules_native(SCRIPTS))

    if violations:
        for v in violations:
            print(v)
        print(f"[lint] {len(violations)} violation(s)")
        return len(violations)
    print("[lint] 0 violations")
    return 0


def run_integrity() -> int:
    issues = []

    print("[integrity] Validating REPOS.json...")
    issues.extend(check_repos_json(ROOT))

    print("[integrity] Checking .gitignore consistency...")
    issues.extend(check_gitignore_consistency(ROOT))

    print("[integrity] Validating directory structure...")
    issues.extend(check_directory_structure(ROOT))

    if issues:
        for i in issues:
            print(i)
        print(f"[integrity] {len(issues)} issue(s)")
        return len(issues)
    print("[integrity] 0 issues")
    return 0


# --- Phase 3: Regression Tests ---


class TestReposLib(unittest.TestCase):
    """Tests for lib/repos.py"""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.repos_file = self.tmpdir / "REPOS.json"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_load_repos_missing_file(self):
        sys.path.insert(0, str(SCRIPTS))
        from lib.repos import load_repos
        result = load_repos(self.tmpdir / "nonexistent.json")
        self.assertEqual(result, [])

    def test_load_repos_valid(self):
        sys.path.insert(0, str(SCRIPTS))
        from lib.repos import load_repos, save_repos
        entries = [{"url": "git@example.com:test.git", "path": "test"}]
        save_repos(entries, self.repos_file)
        result = load_repos(self.repos_file)
        self.assertEqual(result, entries)

    def test_save_repos_format(self):
        sys.path.insert(0, str(SCRIPTS))
        from lib.repos import save_repos
        entries = [{"url": "git@example.com:test.git", "path": "test"}]
        save_repos(entries, self.repos_file)
        text = self.repos_file.read_text(encoding="utf-8")
        self.assertTrue(text.endswith("\n"), "JSON output must end with trailing newline")
        parsed = json.loads(text)
        # Verify 2-space indent by checking re-serialization matches
        expected = json.dumps(parsed, indent=2) + "\n"
        self.assertEqual(text, expected, "JSON output must use 2-space indent")

    def test_load_repos_empty_array(self):
        sys.path.insert(0, str(SCRIPTS))
        from lib.repos import load_repos
        self.repos_file.write_text("[]")
        result = load_repos(self.repos_file)
        self.assertEqual(result, [])


def run_regression() -> int:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestReposLib))

    total = suite.countTestCases()
    print(f"[regression] Running {total} tests...")

    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, "w"))
    result = runner.run(suite)

    passed = total - len(result.failures) - len(result.errors)
    print(f"[regression] {passed}/{total} passed")

    if result.failures or result.errors:
        for test, traceback in result.failures + result.errors:
            print(f"  FAIL: {test}")
            for line in traceback.strip().splitlines():
                print(f"    {line}")
        return len(result.failures) + len(result.errors)
    return 0


def main() -> None:
    failures = 0
    failures += run_lint()
    failures += run_integrity()
    failures += run_regression()
    if failures:
        print(f"\n{failures} check(s) failed.")
        sys.exit(1)
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
