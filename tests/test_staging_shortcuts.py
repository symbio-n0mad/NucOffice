import json
import sys

import pytest

from nucoffice import shortcuts, staging
from nucoffice.paths import Layout, Scope
from nucoffice.registry import Tool

TOOL = Tool(key="demo", display_name="Demo Tool", repo="me/demo", package="demo",
            gui_entry="demo-gui", description="Nur ein Test")


def test_summarize_reads_pyproject_without_running_code(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="demo"\nversion="1.0"\nrequires-python=">=3.11"\n'
        'dependencies=["numpy"]\n[project.optional-dependencies]\ngui=["PySide6"]\n'
        '[project.gui-scripts]\ndemo-gui="demo.app:main"\n'
    )
    (tmp_path / "setup.py").write_text("raise SystemExit('darf nicht laufen')\n")
    (tmp_path / "demo").mkdir()
    (tmp_path / "demo" / "app.py").write_text("def main(): pass\n")
    s = staging.summarize(tmp_path)
    assert (s.name, s.version, s.dependencies) == ("demo", "1.0", ["numpy"])
    assert s.optional["gui"] == ["PySide6"]
    assert s.entry_points == {"demo-gui": "demo.app:main"}
    assert s.python_files == 2 and s.build_hooks == ["setup.py"]


def test_load_staged_checks_repo(tmp_path):
    lay = Layout(root=tmp_path, bin_dir=tmp_path / "bin")
    d = lay.staging_dir / "demo"
    d.mkdir(parents=True)
    (lay.staging_dir / f"demo{staging.MARKER_SUFFIX}").write_text(json.dumps(
        {"key": "demo", "repo": "me/demo", "ref": "v1", "commit": "abc123"}))
    staged = staging.load_staged(TOOL, lay)
    assert staged.commit == "abc123" and staged.path == d
    assert staged.compare_url("old") == "https://github.com/me/demo/compare/old...abc123"
    other = Tool(key="demo", display_name="x", repo="other/demo", package="x", gui_entry="x")
    assert staging.load_staged(other, lay) is None


@pytest.mark.skipif(sys.platform == "win32", reason=".desktop nur unter Linux")
def test_desktop_shortcut_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    cmd = tmp_path / "mit Leerzeichen" / "demo-gui"
    link = shortcuts.create(TOOL, cmd, Scope.USER)
    assert link == tmp_path / "applications" / "nucoffice-demo.desktop"
    text = link.read_text()
    assert f'Exec="{cmd}"' in text and "Name=Demo Tool" in text and "Terminal=false" in text
    shortcuts.remove(TOOL, Scope.USER)
    assert not link.exists()
