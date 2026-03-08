import os
import subprocess
import pytest

from util.venv import Venv


class TestVenvInit:
    def test_python_path_unix(self, tmp_path, monkeypatch):
        monkeypatch.setattr(os, "name", "posix")
        v = Venv(str(tmp_path / "venv"))
        assert v.virtual_python.endswith(os.path.join("venv", "bin", "python"))

    def test_python_path_windows(self, tmp_path, monkeypatch):
        monkeypatch.setattr(os, "name", "nt")
        v = Venv(str(tmp_path / "venv"))
        assert v.virtual_python.endswith(os.path.join("venv", "Scripts", "python.exe"))


class TestHasPip:
    def test_has_pip_true(self, monkeypatch):
        """_has_pip returns True when subprocess returns 0."""
        monkeypatch.setattr(subprocess, "call", lambda *a, **kw: 0)
        v = Venv("/fake/venv")
        assert v._has_pip()

    def test_has_pip_false(self, monkeypatch):
        """_has_pip returns False when subprocess returns non-zero."""
        monkeypatch.setattr(subprocess, "call", lambda *a, **kw: 1)
        v = Venv("/fake/venv")
        assert not v._has_pip()


class TestEnsurePip:
    def test_skips_when_pip_present(self, monkeypatch):
        """_ensure_pip should not call ensurepip if pip already works."""
        calls = []
        monkeypatch.setattr(subprocess, "call", lambda cmd, **kw: calls.append(cmd) or 0)
        v = Venv("/fake/venv")
        v._ensure_pip()
        # Only the _has_pip check should have been called, not ensurepip
        assert len(calls) == 1
        assert "pip" in calls[0]

    def test_bootstraps_when_pip_missing(self, monkeypatch):
        """_ensure_pip should invoke ensurepip when pip check fails."""
        call_log = []

        def mock_call(cmd, **kw):
            call_log.append(cmd)
            # First call is _has_pip check -> fail; second is ensurepip -> succeed
            if "ensurepip" in cmd:
                return 0
            return 1

        monkeypatch.setattr(subprocess, "call", mock_call)
        v = Venv("/fake/venv")
        v._ensure_pip()
        assert any("ensurepip" in cmd for cmd in call_log)


class TestInstallVirtualEnv:
    def test_creates_new_venv(self, tmp_path, monkeypatch):
        """When venv python doesn't exist, it should create one and ensure pip."""
        venv_dir = str(tmp_path / "new_venv")
        v = Venv(venv_dir)

        created = []
        monkeypatch.setattr("venv.EnvBuilder.create", lambda self, path: created.append(path))
        # Make _ensure_pip a no-op
        monkeypatch.setattr(v, "_ensure_pip", lambda: None)

        v.install_virtual_env()
        assert len(created) == 1

    def test_skips_creation_when_exists(self, tmp_path, monkeypatch):
        """When venv python already exists, it should skip creation but still ensure pip."""
        venv_dir = tmp_path / "existing_venv"
        bin_dir = venv_dir / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "python").touch()

        v = Venv(str(venv_dir))

        pip_checked = []
        monkeypatch.setattr(v, "_ensure_pip", lambda: pip_checked.append(True))

        v.install_virtual_env()
        assert len(pip_checked) == 1


class TestIsVenv:
    def test_true_when_prefix_matches(self, monkeypatch):
        monkeypatch.setattr("sys.prefix", "/my/venv")
        v = Venv("/my/venv")
        assert v.is_venv()

    def test_false_when_prefix_differs(self, monkeypatch):
        monkeypatch.setattr("sys.prefix", "/other/path")
        v = Venv("/my/venv")
        assert not v.is_venv()
