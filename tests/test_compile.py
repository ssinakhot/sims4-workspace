import os
import zipfile
import pytest


@pytest.fixture(autouse=True)
def _mock_settings(mock_settings):
    mock_settings.devmode_parity = True


class TestCompileSlim:
    def test_compiles_py_files_with_parity(self, tmp_path, mock_settings):
        mock_settings.devmode_parity = True
        from util.compile import compile_slim

        src = tmp_path / "modsrc"
        src.mkdir()
        (src / "__init__.py").write_text("# init")
        (src / "module.py").write_text("x = 1")

        zf_path = tmp_path / "out.zip"
        zf = zipfile.PyZipFile(str(zf_path), mode='w', allowZip64=True, optimize=2)
        compile_slim(str(src), zf)
        zf.close()

        names = zipfile.ZipFile(str(zf_path)).namelist()
        assert len(names) > 0
        assert any(n.endswith(".pyc") for n in names)

    def test_compiles_without_parity(self, tmp_path, mock_settings, monkeypatch):
        import util.compile as compile_mod
        monkeypatch.setattr(compile_mod, "devmode_parity", False)

        from util.compile import compile_slim

        src = tmp_path / "modsrc"
        src.mkdir()
        (src / "__init__.py").write_text("# init")
        (src / "helper.py").write_text("y = 2")

        zf_path = tmp_path / "out.zip"
        zf = zipfile.PyZipFile(str(zf_path), mode='w', allowZip64=True, optimize=2)
        compile_slim(str(src), zf)
        zf.close()

        names = zipfile.ZipFile(str(zf_path)).namelist()
        assert len(names) > 0


class TestCompileFull:
    def test_includes_non_py_files(self, tmp_path, mock_settings):
        from util.compile import compile_full

        src = tmp_path / "modsrc"
        src.mkdir()
        (src / "__init__.py").write_text("# init")
        (src / "data.txt").write_text("some data")
        (src / "module.py").write_text("x = 1")

        zf_path = tmp_path / "out.zip"
        zf = zipfile.PyZipFile(str(zf_path), mode='w', allowZip64=True, optimize=2)
        compile_full(str(src), zf)
        zf.close()

        names = zipfile.ZipFile(str(zf_path)).namelist()
        assert any("data.txt" in n for n in names)
        assert any(n.endswith(".pyc") for n in names)


class TestCompileSrc:
    def test_creates_ts4script(self, tmp_path, mock_settings):
        from util.compile import compile_src

        src = tmp_path / "modsrc"
        src.mkdir()
        (src / "__init__.py").write_text("# init")
        (src / "mod.py").write_text("print('hello')")

        build = tmp_path / "output"
        mods = tmp_path / "moddir"

        compile_src("TestCreator", str(src), str(build), str(mods), "TestMod")

        ts4script = os.path.join(str(build), "TestCreator_TestMod.ts4script")
        assert os.path.isfile(ts4script)

        mod_ts4 = os.path.join(str(mods), "TestCreator_TestMod", "TestCreator_TestMod.ts4script")
        assert os.path.isfile(mod_ts4)

    def test_clears_old_builds(self, tmp_path, mock_settings):
        from util.compile import compile_src

        src = tmp_path / "modsrc"
        src.mkdir()
        (src / "__init__.py").write_text("# init")

        build = tmp_path / "output"
        build.mkdir()
        old_file = build / "old_artifact.txt"
        old_file.write_text("old")

        mods = tmp_path / "moddir"

        compile_src("TestCreator", str(src), str(build), str(mods), "TestMod")

        assert not old_file.exists()
