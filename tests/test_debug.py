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
