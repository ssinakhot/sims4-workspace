import os
import sys
import pytest

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_settings(monkeypatch, tmp_path):
    """Mock the settings module so tests don't need a real settings.py."""
    import types
    settings = types.ModuleType("settings")

    settings.creator_name = "TestCreator"
    settings.project_name = "TestProject"
    settings.mods_folder = str(tmp_path / "Mods")
    settings.src_path = str(tmp_path / "src")
    settings.build_path = str(tmp_path / "build")
    settings.assets_path = str(tmp_path / "assets")

    # Create the directories
    os.makedirs(settings.mods_folder, exist_ok=True)
    os.makedirs(settings.src_path, exist_ok=True)
    os.makedirs(settings.build_path, exist_ok=True)
    os.makedirs(settings.assets_path, exist_ok=True)

    monkeypatch.setitem(sys.modules, "settings", settings)
    return settings


@pytest.fixture
def mod_folder(mock_settings):
    """Return the mod folder path (CreatorName_ProjectName inside Mods)."""
    path = os.path.join(mock_settings.mods_folder,
                        mock_settings.creator_name + "_" + mock_settings.project_name)
    os.makedirs(path, exist_ok=True)
    return path
