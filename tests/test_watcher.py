import os
import pytest

from util.watcher import get_scripts_path, exec_cmd, watcher_folder_exists, watcher_folder_remove


class TestGetScriptsPath:
    def test_with_creator_name(self, tmp_path):
        result = get_scripts_path("Creator", str(tmp_path), "MyMod")
        assert result == os.path.join(str(tmp_path), "Creator_MyMod", "Scripts")

    def test_without_creator_name(self, tmp_path):
        result = get_scripts_path("", str(tmp_path), "MyMod")
        assert result == os.path.join(str(tmp_path), "MyMod", "Scripts")

    def test_default_mod_name(self, tmp_path):
        result = get_scripts_path("Creator", str(tmp_path))
        assert result == os.path.join(str(tmp_path), "Creator_Untitled", "Scripts")


class TestExecCmd:
    def test_successful_command(self):
        assert exec_cmd("echo", "hello")

    def test_failed_command(self):
        assert not exec_cmd("false", "")

    def test_nonexistent_command(self):
        assert not exec_cmd("nonexistent_cmd_xyz", "")


class TestWatcherFolderExists:
    def test_returns_false_when_missing(self, tmp_path):
        assert not watcher_folder_exists("Creator", str(tmp_path), "MyMod")

    def test_returns_true_when_dir_exists(self, tmp_path):
        scripts = os.path.join(str(tmp_path), "Creator_MyMod", "Scripts")
        os.makedirs(scripts)
        assert watcher_folder_exists("Creator", str(tmp_path), "MyMod")

    def test_returns_true_when_file_exists(self, tmp_path):
        mod_dir = os.path.join(str(tmp_path), "Creator_MyMod")
        os.makedirs(mod_dir)
        # Scripts as a file instead of a dir
        open(os.path.join(mod_dir, "Scripts"), "w").close()
        assert watcher_folder_exists("Creator", str(tmp_path), "MyMod")


class TestWatcherFolderRemove:
    def test_removes_scripts_directory(self, tmp_path):
        scripts = os.path.join(str(tmp_path), "Creator_MyMod", "Scripts")
        os.makedirs(scripts)
        # Add a file inside Scripts
        open(os.path.join(scripts, "test.py"), "w").close()

        watcher_folder_remove("Creator", str(tmp_path), "MyMod")
        assert not os.path.exists(scripts)

    def test_removes_scripts_file(self, tmp_path):
        mod_dir = os.path.join(str(tmp_path), "Creator_MyMod")
        os.makedirs(mod_dir)
        scripts_file = os.path.join(mod_dir, "Scripts")
        open(scripts_file, "w").close()

        watcher_folder_remove("Creator", str(tmp_path), "MyMod")
        assert not os.path.exists(scripts_file)

    def test_noop_when_missing(self, tmp_path):
        # Should not raise
        watcher_folder_remove("Creator", str(tmp_path), "MyMod")

    def test_preserves_parent_directory(self, tmp_path):
        mod_dir = os.path.join(str(tmp_path), "Creator_MyMod")
        scripts = os.path.join(mod_dir, "Scripts")
        os.makedirs(scripts)

        watcher_folder_remove("Creator", str(tmp_path), "MyMod")
        assert os.path.exists(mod_dir)
        assert not os.path.exists(scripts)
