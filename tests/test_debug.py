import os
import pytest


@pytest.fixture(autouse=True)
def _mock_settings(mock_settings):
    mock_settings.decompiler_timeout = 10.0


class TestInstallDebugMod:
    def test_creates_ts4script(self, tmp_path):
        from util.debug import install_debug_mod

        mod_src = str(tmp_path / "debug_cmd.py")
        with open(mod_src, "w") as f:
            f.write("print('debug')\n")

        mods_dir = str(tmp_path / "GameMods")
        os.makedirs(mods_dir)

        install_debug_mod(mod_src, mods_dir, "debug-cmd", "TestMod_Debug")

        expected = os.path.join(mods_dir, "TestMod_Debug", "debug-cmd.ts4script")
        assert os.path.isfile(expected)

    def test_ts4script_is_valid_zip(self, tmp_path):
        import zipfile
        from util.debug import install_debug_mod

        mod_src = str(tmp_path / "debug_cmd.py")
        with open(mod_src, "w") as f:
            f.write("x = 1\n")

        mods_dir = str(tmp_path / "GameMods")
        os.makedirs(mods_dir)

        install_debug_mod(mod_src, mods_dir, "test-mod", "TestFolder")

        ts4 = os.path.join(mods_dir, "TestFolder", "test-mod.ts4script")
        assert zipfile.is_zipfile(ts4)
        with zipfile.ZipFile(ts4) as zf:
            assert len(zf.namelist()) > 0


class TestRemoveDebugMods:
    def test_removes_ts4script_files(self, tmp_path):
        from util.debug import remove_debug_mods

        mod_dir = tmp_path / "Mods" / "DebugFolder"
        mod_dir.mkdir(parents=True)
        (mod_dir / "mod1.ts4script").write_text("fake")
        (mod_dir / "mod2.ts4script").write_text("fake")
        (mod_dir / "readme.txt").write_text("keep")

        remove_debug_mods(str(tmp_path / "Mods"), "DebugFolder")

        assert not (mod_dir / "mod1.ts4script").exists()
        assert not (mod_dir / "mod2.ts4script").exists()
        assert (mod_dir / "readme.txt").exists()

    def test_noop_when_folder_missing(self, tmp_path):
        from util.debug import remove_debug_mods
        # Should not raise
        remove_debug_mods(str(tmp_path), "NonExistent")


class TestDebugTeardown:
    def test_removes_entire_folder(self, tmp_path):
        from util.debug import debug_teardown

        mod_dir = tmp_path / "Mods" / "DebugFolder"
        mod_dir.mkdir(parents=True)
        (mod_dir / "some_file.ts4script").write_text("fake")

        debug_teardown(str(tmp_path / "Mods"), "DebugFolder")
        assert not mod_dir.exists()

    def test_noop_when_missing(self, tmp_path):
        from util.debug import debug_teardown
        # Should not raise
        debug_teardown(str(tmp_path), "NonExistent")


class TestDebugInstallEgg:
    @pytest.fixture
    def fake_egg(self, tmp_path):
        """Create a fake PyCharm debug egg (zip with some files)."""
        import zipfile
        egg_path = str(tmp_path / "pydevd-pycharm.egg")
        with zipfile.ZipFile(egg_path, "w") as zf:
            zf.writestr("pydevd/__init__.py", "# pydevd init\n")
            zf.writestr("pydevd/debugger.py", "# debugger code\n")
            zf.writestr("EGG-INFO/PKG-INFO", "Name: pydevd-pycharm\n")
        return egg_path

    @pytest.fixture
    def fake_sys_folder(self, tmp_path):
        """Create a fake sys folder with a ctypes directory."""
        sys_folder = tmp_path / "fakepython"
        ctypes_dir = sys_folder / "Lib" / "ctypes"
        ctypes_dir.mkdir(parents=True)
        (ctypes_dir / "__init__.py").write_text("# ctypes init\n")
        (ctypes_dir / "_endian.py").write_text("# endian\n")
        cache_dir = ctypes_dir / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "__init__.cpython-37.pyc").write_bytes(b"fakepyc")
        return str(sys_folder)

    def test_creates_ts4script_with_egg_and_ctypes(self, tmp_path, fake_egg, fake_sys_folder, monkeypatch):
        import zipfile
        from util.debug import debug_install_egg

        monkeypatch.setattr("util.debug.get_sys_folder", lambda: fake_sys_folder)

        mods_dir = str(tmp_path / "Mods")
        os.makedirs(mods_dir, exist_ok=True)

        debug_install_egg(fake_egg, mods_dir, "pycharm-debug", "DebugFolder")

        mod_path = os.path.join(mods_dir, "DebugFolder", "pycharm-debug.ts4script")
        assert os.path.isfile(mod_path)
        assert zipfile.is_zipfile(mod_path)

        with zipfile.ZipFile(mod_path) as zf:
            names = zf.namelist()
            # Egg contents are included
            assert "pydevd/__init__.py" in names
            assert "pydevd/debugger.py" in names
            assert "EGG-INFO/PKG-INFO" in names
            # ctypes files are included
            assert "ctypes/__init__.py" in names
            assert "ctypes/_endian.py" in names
            # __pycache__ is excluded
            pycache_entries = [n for n in names if "__pycache__" in n]
            assert pycache_entries == []

    def test_replaces_existing_mod(self, tmp_path, fake_egg, fake_sys_folder, monkeypatch):
        from util.debug import debug_install_egg

        monkeypatch.setattr("util.debug.get_sys_folder", lambda: fake_sys_folder)

        mods_dir = str(tmp_path / "Mods")
        mod_dir = os.path.join(mods_dir, "DebugFolder")
        os.makedirs(mod_dir)
        old_mod = os.path.join(mod_dir, "pycharm-debug.ts4script")
        with open(old_mod, "w") as f:
            f.write("old content")

        debug_install_egg(fake_egg, mods_dir, "pycharm-debug", "DebugFolder")

        # File should be replaced, not contain old content
        with open(old_mod, "rb") as f:
            content = f.read()
        assert b"old content" not in content
