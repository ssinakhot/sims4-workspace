import os
import pytest

from util.sync_packages import remove_tl_packages, copy_tl_packages, sync_packages


class TestRemoveTlPackages:
    def test_removes_packages(self, tmp_path):
        (tmp_path / "mod_a.package").write_bytes(b"data")
        (tmp_path / "mod_b.package").write_bytes(b"data")
        (tmp_path / "keep.txt").write_text("keep")

        count = remove_tl_packages(str(tmp_path))

        assert count == 2
        assert not (tmp_path / "mod_a.package").exists()
        assert not (tmp_path / "mod_b.package").exists()
        assert (tmp_path / "keep.txt").exists()

    def test_empty_directory(self, tmp_path):
        count = remove_tl_packages(str(tmp_path))
        assert count == 0

    def test_only_top_level(self, tmp_path):
        (tmp_path / "top.package").write_bytes(b"data")
        sub = tmp_path / "subdir"
        sub.mkdir()
        (sub / "nested.package").write_bytes(b"data")

        count = remove_tl_packages(str(tmp_path))

        assert count == 1
        assert (sub / "nested.package").exists()


class TestCopyTlPackages:
    def test_copies_files(self, tmp_path):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        dst.mkdir()

        (src / "mod.package").write_bytes(b"moddata")
        (src / "tuning.package").write_bytes(b"tuning")

        failed = []
        count = copy_tl_packages(str(src), str(dst), failed)

        assert count == 2
        assert (dst / "mod.package").read_bytes() == b"moddata"
        assert (dst / "tuning.package").read_bytes() == b"tuning"
        assert len(failed) == 0

    def test_skips_gitkeep(self, tmp_path):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        dst.mkdir()

        (src / ".gitkeep").write_text("")
        (src / "mod.package").write_bytes(b"data")

        failed = []
        count = copy_tl_packages(str(src), str(dst), failed)

        assert count == 1
        assert not (dst / ".gitkeep").exists()


class TestSyncPackages:
    def test_full_sync(self, tmp_path):
        assets = tmp_path / "assets"
        mods = tmp_path / "Mods"
        build = tmp_path / "build"
        assets.mkdir()
        mods.mkdir()
        build.mkdir()

        (assets / "new_mod.package").write_bytes(b"new")

        sync_packages(
            assets_path=str(assets),
            mods_folder=str(mods),
            build_path=str(build),
            creator_name="Test",
            project_name="Mod",
        )

        mod_dir = mods / "Test_Mod"
        assert mod_dir.exists()
        assert (mod_dir / "new_mod.package").read_bytes() == b"new"
        assert (build / "new_mod.package").read_bytes() == b"new"
