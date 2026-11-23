import shutil
import subprocess
import zipfile

import pytest

from nucoffice.sources import bundled


def _project(path):
    path.mkdir()
    (path / "pyproject.toml").write_text('[project]\nname="demo"\nversion="1.2.3"\n')
    (path / "demo.py").write_text("print('hi')\n")
    (path / ".venv").mkdir()
    (path / ".venv" / "huge.bin").write_text("x")
    return path


def test_create_extract_roundtrip(tmp_path):
    src, base = _project(tmp_path / "src"), tmp_path / "bundled"
    entry = bundled.create("demo", src, base)
    assert entry.file == "demo-1.2.3.zip" and entry.ref == "v1.2.3" and entry.commit is None
    assert bundled.available("demo", base) == entry
    with zipfile.ZipFile(base / entry.file) as zf:
        assert not any(".venv" in n for n in zf.namelist())
    out = bundled.extract(entry, tmp_path / "out", base)
    assert (out / "demo.py").exists() and (out / "pyproject.toml").exists()


def test_new_version_replaces_old_archive(tmp_path):
    src, base = _project(tmp_path / "src"), tmp_path / "bundled"
    bundled.create("demo", src, base)
    (src / "pyproject.toml").write_text('[project]\nname="demo"\nversion="2.0"\n')
    bundled.create("demo", src, base)
    assert sorted(p.name for p in base.glob("*.zip")) == ["demo-2.0.zip"]


def test_checksum_mismatch_is_rejected(tmp_path):
    src, base = _project(tmp_path / "src"), tmp_path / "bundled"
    entry = bundled.create("demo", src, base)
    with open(base / entry.file, "ab") as fh:
        fh.write(b"kaputt")
    with pytest.raises(bundled.BundleError, match="Prüfsumme"):
        bundled.extract(entry, tmp_path / "out", base)


def test_zip_slip_is_rejected(tmp_path):
    base = tmp_path / "bundled"
    base.mkdir()
    with zipfile.ZipFile(base / "evil.zip", "w") as zf:
        zf.writestr("../draussen.txt", "x")
    entry = bundled.BundledTool("evil", "evil.zip", bundled.sha256_of(base / "evil.zip"),
                                None, "x", None)
    with pytest.raises(bundled.BundleError, match="Unzulässiger Pfad"):
        bundled.extract(entry, tmp_path / "out", base)
    assert not (tmp_path / "draussen.txt").exists()


@pytest.mark.skipif(shutil.which("git") is None, reason="git fehlt")
def test_git_repo_packs_only_committed_files(tmp_path):
    src, base = _project(tmp_path / "src"), tmp_path / "bundled"
    (src / ".gitignore").write_text(".venv/\n")
    git = ["git", "-C", str(src), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-qm", "x"], check=True)
    (src / "lokal.dat").write_text("nicht eingecheckt")
    entry = bundled.create("demo", src, base)
    assert entry.commit and len(entry.commit) == 40
    with zipfile.ZipFile(base / entry.file) as zf:
        names = zf.namelist()
    assert "demo/demo.py" in names and not any("lokal.dat" in n for n in names)
