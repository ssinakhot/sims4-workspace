import os
import sys
import pytest


@pytest.fixture(autouse=True)
def _mock_settings(mock_settings):
    """exec_cli imports settings.decompiler_timeout at module level."""
    mock_settings.decompiler_timeout = 10.0


class TestExecCliCommandResolution:
    """Test that exec_cli builds the correct command list."""

    def test_file_path_used_directly(self, tmp_path):
        """When package is an existing file path, it should be invoked directly."""
        from util.exec import exec_cli

        script = tmp_path / "my_tool"
        script.write_text("#!/usr/bin/env python3\nimport sys; sys.exit(0)\n")
        script.chmod(0o755)

        success, result = exec_cli(str(script), ["--help"])
        # The command should have run the script directly (not via python -m)
        assert result is not None

    def test_python3_uses_sys_executable(self):
        """When package is 'python3', it should use sys.executable."""
        from util.exec import exec_cli

        success, result = exec_cli("python3", ["--version"])
        assert success
        assert "Python" in result.stdout

    def test_console_script_preferred_over_dash_m(self, tmp_path, monkeypatch):
        """When a console script exists in the scripts folder, use it
        instead of python -m."""
        import util.exec as exec_mod
        from util.exec import exec_cli

        # Create a fake console script
        script = tmp_path / "fakepkg"
        script.write_text(
            "#!/usr/bin/env python3\nimport sys; print('console_script'); sys.exit(0)\n"
        )
        script.chmod(0o755)

        # Point get_sys_scripts_folder to our tmp dir
        monkeypatch.setattr(exec_mod, "get_sys_scripts_folder", lambda: str(tmp_path))

        success, result = exec_cli("fakepkg", [])
        assert success
        assert "console_script" in result.stdout

    def test_falls_back_to_dash_m_when_no_script(self, tmp_path, monkeypatch):
        """When no console script exists, fall back to python -m."""
        import util.exec as exec_mod
        from util.exec import exec_cli

        # Point to an empty dir so no script is found
        monkeypatch.setattr(exec_mod, "get_sys_scripts_folder", lambda: str(tmp_path))

        # 'json.tool' is a stdlib module that supports -m invocation
        success, result = exec_cli("json.tool", ["--help"])
        assert success

    def test_timeout_returns_false(self, mock_settings):
        """Commands that exceed the timeout should return (False, TimeoutExpired)."""
        from subprocess import TimeoutExpired
        from util.exec import exec_cli

        mock_settings.decompiler_timeout = 0.001

        success, result = exec_cli("python3", ["-c", "import time; time.sleep(5)"],
                                   timeout=0.001)
        assert not success
        assert isinstance(result, TimeoutExpired)
