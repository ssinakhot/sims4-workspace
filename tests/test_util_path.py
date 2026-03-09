import os
import sys
import pytest

from util.path import (
    get_rel_path,
    get_file_stem,
    replace_extension,
    get_default_executable_extension,
    get_sys_path,
    get_sys_folder,
    get_sys_scripts_folder,
    get_full_filepath,
    ensure_path_created,
    remove_dir,
    remove_file,
)


class TestGetRelPath:
    def test_basic(self):
        result = get_rel_path("/home/user/project/src/main.py", "/home/user/project")
        assert result == os.path.join("src", "main.py")

    def test_same_path(self):
        result = get_rel_path("/home/user/project", "/home/user/project")
        assert result == "."

    def test_nested(self):
        result = get_rel_path("/a/b/c/d/e.txt", "/a/b")
        assert result == os.path.join("c", "d", "e.txt")


class TestGetFileStem:
    def test_simple(self):
        assert get_file_stem("test.py") == "test"

    def test_with_path(self):
        assert get_file_stem("/home/user/test.py") == "test"

    def test_multiple_dots(self):
        assert get_file_stem("my.test.file.py") == "my.test.file"

    def test_no_extension(self):
        assert get_file_stem("Makefile") == "Makefile"


class TestReplaceExtension:
    def test_basic(self):
        result = replace_extension("test.py", "pyc")
        assert result.endswith("test.pyc")

    def test_with_path(self):
        result = replace_extension("/home/user/test.py", "txt")
        assert result.endswith("test.txt")
        assert "/home/user" in result or "home" in result


class TestGetDefaultExecutableExtension:
    def test_returns_string(self):
        result = get_default_executable_extension()
        assert isinstance(result, str)

    def test_matches_sys_executable(self):
        from pathlib import Path
        expected = Path(sys.executable).suffix
        assert get_default_executable_extension() == expected


class TestGetSysPath:
    def test_returns_executable(self):
        assert get_sys_path() == sys.executable

    def test_is_absolute(self):
        assert os.path.isabs(get_sys_path())


class TestGetSysFolder:
    def test_returns_parent_of_executable(self):
        result = get_sys_folder()
        assert result == str(os.path.dirname(sys.executable))


class TestGetSysScriptsFolder:
    def test_returns_existing_directory(self):
        result = get_sys_scripts_folder()
        assert os.path.isdir(result)

    def test_unix_appends_bin(self, monkeypatch):
        monkeypatch.setattr(os, "name", "posix")
        # Simulate a sys folder that doesn't end with 'bin'
        monkeypatch.setattr("util.path.get_sys_folder", lambda: "/usr/local")
        result = get_sys_scripts_folder()
        assert result == "/usr/local/bin"

    def test_unix_already_bin(self, monkeypatch):
        monkeypatch.setattr(os, "name", "posix")
        monkeypatch.setattr("util.path.get_sys_folder", lambda: "/usr/local/bin")
        result = get_sys_scripts_folder()
        assert result == "/usr/local/bin"

    def test_windows_appends_scripts(self, monkeypatch):
        monkeypatch.setattr(os, "name", "nt")
        monkeypatch.setattr("util.path.get_sys_folder", lambda: "C:\\Python37")
        result = get_sys_scripts_folder()
        assert result == os.path.join("C:\\Python37", "Scripts")

    def test_windows_already_bin(self, monkeypatch):
        monkeypatch.setattr(os, "name", "nt")
        monkeypatch.setattr("util.path.get_sys_folder", lambda: "C:\\Python37\\bin")
        result = get_sys_scripts_folder()
        assert result == "C:\\Python37\\bin"


class TestGetFullFilepath:
    def test_finds_exact_file_unix(self, tmp_path):
        # On Unix, get_full_filepath globs for the exact base_name (no wildcard)
        (tmp_path / "myfile").write_text("hello")
        result = get_full_filepath(str(tmp_path), "myfile")
        assert result.endswith("myfile")

    def test_finds_file_with_extension_windows(self, tmp_path, monkeypatch):
        # On Windows, it globs for base_name.*
        monkeypatch.setattr(os, "name", "nt")
        (tmp_path / "myfile.txt").write_text("hello")
        result = get_full_filepath(str(tmp_path), "myfile")
        assert result.endswith("myfile.txt")

    def test_raises_on_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            get_full_filepath(str(tmp_path), "nonexistent")


class TestEnsurePathCreated:
    def test_creates_directory(self, tmp_path):
        new_dir = str(tmp_path / "a" / "b" / "c")
        ensure_path_created(new_dir)
        assert os.path.isdir(new_dir)

    def test_existing_directory(self, tmp_path):
        # Should not raise
        ensure_path_created(str(tmp_path))
        assert os.path.isdir(str(tmp_path))


class TestRemoveDir:
    def test_removes_directory(self, tmp_path):
        target = tmp_path / "target"
        target.mkdir()
        (target / "file.txt").write_text("hello")
        (target / "subdir").mkdir()
        (target / "subdir" / "nested.txt").write_text("world")

        remove_dir(str(target))
        assert not target.exists()

    def test_nonexistent_directory(self, tmp_path):
        # Should not raise
        remove_dir(str(tmp_path / "nonexistent"))


class TestRemoveFile:
    def test_removes_file(self, tmp_path):
        target = tmp_path / "file.txt"
        target.write_text("hello")
        remove_file(str(target))
        assert not target.exists()

    def test_nonexistent_file(self, tmp_path):
        # Should not raise
        remove_file(str(tmp_path / "nonexistent.txt"))
