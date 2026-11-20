import sys
import time

import pytest

from nucoffice import process
from nucoffice.paths import Scope, layout
from nucoffice.registry import load_registry
from nucoffice.sources.github import _newest_tag
from nucoffice.state import InstalledTool, State


def test_registry_loads():
    reg = load_registry()
    assert {"plotspe", "plotrde", "activitypartitioner", "nucdb", "hdtv"} <= set(reg)
    assert reg["plotrde"].requirement == "radonlab[gui]"
    assert reg["hdtv"].platforms == ("linux",)


def test_registry_rejects_unknown_field(tmp_path):
    f = tmp_path / "t.toml"
    f.write_text('[tools.x]\ndisplay_name="X"\nrepo="a/b"\npackage="x"\ngui_entry="x"\ntypo=1\n')
    with pytest.raises(ValueError, match="typo"):
        load_registry(f)


def test_layout_paths():
    lay = layout(Scope.USER)
    assert lay.nucdb_dir == lay.root / "data" / "nucdb"
    assert lay.venv_dir("plotspe").parent == lay.tool_dir("plotspe")


def test_state_roundtrip(tmp_path):
    s = State(tmp_path / "state.json")
    s.set(InstalledTool("plotrde", "0.1.0", "github", "v0.1.0", "abc", "2026-11-20T12:00:00"))
    assert State(tmp_path / "state.json").get("plotrde").version == "0.1.0"
    s.remove("plotrde")
    assert State(tmp_path / "state.json").get("plotrde") is None


def test_newest_tag():
    assert _newest_tag(["v24.01", "v24.10", "v24.03", "v9.9"]) == "v24.10"
    assert _newest_tag(["v1.2.0", "v1.10.0"]) == "v1.10.0"


def test_start_status_stop(tmp_path):
    cmd = [sys.executable, "-c", "import time; time.sleep(60)"]
    info = process.start("dummy", cmd, base=tmp_path)
    assert process.status("dummy", base=tmp_path).pid == info.pid
    with pytest.raises(RuntimeError):
        process.start("dummy", cmd, base=tmp_path)
    assert process.stop("dummy", timeout=5, base=tmp_path)
    time.sleep(0.1)
    assert process.status("dummy", base=tmp_path) is None
    assert not process.stop("dummy", base=tmp_path)
