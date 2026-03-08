import os
import pytest

from util.path import (
    get_rel_path,
    get_file_stem,
    replace_extension,
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
