import os
import pytest
from zipfile import ZipFile

from util.bundle_build import bundle_build


class TestBundleBuild:
    def test_creates_zip(self, tmp_path):
        build = tmp_path / "build"
        build.mkdir()
        (build / "mod.ts4script").write_bytes(b"scriptdata")
        (build / "tuning.package").write_bytes(b"tuningdata")

        bundle_build(str(build), "Creator", "MyMod")

        zip_path = build / "Creator_MyMod.zip"
        assert zip_path.exists()

        with ZipFile(str(zip_path), "r") as zf:
            names = zf.namelist()
            assert "mod.ts4script" in names
            assert "tuning.package" in names

    def test_replaces_existing_zip(self, tmp_path):
        build = tmp_path / "build"
        build.mkdir()
        (build / "mod.ts4script").write_bytes(b"data")

        # Create initial zip
        bundle_build(str(build), "Creator", "Mod")
        zip_path = build / "Creator_Mod.zip"
        first_size = zip_path.stat().st_size

        # Add more content and rebuild
        (build / "extra.package").write_bytes(b"extra")
        # Remove old zip first since it would be included in copytree
        os.remove(str(zip_path))
        bundle_build(str(build), "Creator", "Mod")
        assert zip_path.exists()
