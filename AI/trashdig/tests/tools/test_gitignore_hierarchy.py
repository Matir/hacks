from trashdig.tools.gitignore import (
    HierarchicalGitIgnore,
    sanitize_gitignore_lines,
    walk_workspace,
)


def test_sanitize_gitignore_lines():
    raw = [
        "  ",
        "",
        "# This is a bare comment",
        "   # Indented bare comment",
        r"\#escaped_hash.py",
        "normal.txt   ",
        r"trailing_space.txt\  ",
        "*.log",
    ]
    sanitized = sanitize_gitignore_lines(raw)
    assert r"\#escaped_hash.py" in sanitized
    assert "normal.txt" in sanitized
    assert r"trailing_space.txt\ " in sanitized
    assert "*.log" in sanitized
    assert "# This is a bare comment" not in sanitized
    assert "   # Indented bare comment" not in sanitized


def test_slash_anchoring_precision(tmp_path):
    # Setup directories
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "sub").mkdir()

    # Files to test:
    # 1. /foo/bar inside src/.gitignore -> should anchor to src/ (matches src/foo/bar, not src/sub/foo/bar)
    # 2. foo/bar (middle slash, no leading slash) inside src/.gitignore -> ALSO anchors to src/
    # 3. baz (no slashes) inside src/.gitignore -> matches anywhere under src/
    (tmp_path / "src" / ".gitignore").write_text(
        "/leading/match.txt\nmiddle/match.txt\nfloating.log\n"
    )

    (tmp_path / "src" / "leading").mkdir()
    (tmp_path / "src" / "leading" / "match.txt").write_text("a")
    (tmp_path / "src" / "sub" / "leading").mkdir()
    (tmp_path / "src" / "sub" / "leading" / "match.txt").write_text("b")

    (tmp_path / "src" / "middle").mkdir()
    (tmp_path / "src" / "middle" / "match.txt").write_text("c")
    (tmp_path / "src" / "sub" / "middle").mkdir()
    (tmp_path / "src" / "sub" / "middle" / "match.txt").write_text("d")

    (tmp_path / "src" / "floating.log").write_text("e")
    (tmp_path / "src" / "sub" / "floating.log").write_text("f")

    resolver = HierarchicalGitIgnore(workspace_root=str(tmp_path))

    # /leading/match.txt in src/.gitignore -> src/leading/match.txt ignored, src/sub/leading/match.txt NOT ignored
    assert resolver.is_ignored("src/leading/match.txt") is True
    assert resolver.is_ignored("src/sub/leading/match.txt") is False

    # middle/match.txt in src/.gitignore -> src/middle/match.txt ignored, src/sub/middle/match.txt NOT ignored
    assert resolver.is_ignored("src/middle/match.txt") is True
    assert resolver.is_ignored("src/sub/middle/match.txt") is False

    # floating.log in src/.gitignore -> both src/floating.log and src/sub/floating.log ignored
    assert resolver.is_ignored("src/floating.log") is True
    assert resolver.is_ignored("src/sub/floating.log") is True


def test_negation_and_parent_dir_lockout(tmp_path):
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "app.log").write_text("a")
    (tmp_path / "logs" / "important.log").write_text("b")

    (tmp_path / "vendor").mkdir()
    (tmp_path / "vendor" / "lib.py").write_text("c")

    # Root .gitignore ignores all logs except important.log in logs, AND excludes directory vendor/
    (tmp_path / ".gitignore").write_text("logs/*.log\n!logs/important.log\nvendor/\n")

    # In vendor/.gitignore, try to negate lib.py
    (tmp_path / "vendor" / ".gitignore").write_text("!lib.py\n")

    resolver = HierarchicalGitIgnore(workspace_root=str(tmp_path))

    # logs/app.log should be ignored, logs/important.log should be included via negation !
    assert resolver.is_ignored("logs/app.log") is True
    assert resolver.is_ignored("logs/important.log") is False

    # vendor/ directory was hard-excluded by root .gitignore -> vendor/lib.py CANNOT be un-ignored by deeper ! rule
    assert resolver.is_ignored("vendor/lib.py") is True


def test_walk_workspace_directory_pruning(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("hello")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "pkg.js").write_text("js")

    (tmp_path / ".gitignore").write_text("node_modules/\n")

    files = list(walk_workspace(workspace_root=str(tmp_path)))
    assert "src/main.py" in files
    assert "node_modules/pkg.js" not in files
