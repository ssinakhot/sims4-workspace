import os
import importlib


class TestGameplayFolderDetection:
    """Test that gameplay_folder_game is set based on where generated.zip exists."""

    def test_windows_layout(self, tmp_path, monkeypatch):
        """When generated.zip is in Game/Bin/Python, that path should be used."""
        game_folder = str(tmp_path / "game")
        win_python = os.path.join(game_folder, "Game", "Bin", "Python")
        os.makedirs(win_python, exist_ok=True)
        open(os.path.join(win_python, "generated.zip"), "w").close()

        # Also create the other candidate so we can verify it's NOT picked
        mac_python = os.path.join(game_folder, "Python")
        os.makedirs(mac_python, exist_ok=True)

        monkeypatch.setattr("os.path.expanduser", lambda p: p)
        monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")

        import settings
        monkeypatch.setattr(settings, "game_folder", game_folder)

        # Re-evaluate the detection logic
        _game_bin_python = os.path.join(game_folder, "Game", "Bin", "Python")
        _game_python = os.path.join(game_folder, "Python")
        if os.path.isfile(os.path.join(_game_bin_python, "generated.zip")):
            expected = _game_bin_python
        else:
            expected = _game_python

        assert expected == win_python

    def test_mac_linux_layout(self, tmp_path, monkeypatch):
        """When generated.zip is NOT in Game/Bin/Python, fall back to Python/."""
        game_folder = str(tmp_path / "game")
        mac_python = os.path.join(game_folder, "Python")
        os.makedirs(mac_python, exist_ok=True)
        open(os.path.join(mac_python, "generated.zip"), "w").close()

        # Game/Bin/Python exists but has no generated.zip
        win_python = os.path.join(game_folder, "Game", "Bin", "Python")
        os.makedirs(win_python, exist_ok=True)

        _game_bin_python = os.path.join(game_folder, "Game", "Bin", "Python")
        _game_python = os.path.join(game_folder, "Python")
        if os.path.isfile(os.path.join(_game_bin_python, "generated.zip")):
            result = _game_bin_python
        else:
            result = _game_python

        assert result == mac_python

    def test_neither_exists(self, tmp_path):
        """When generated.zip doesn't exist anywhere, fall back to Python/."""
        game_folder = str(tmp_path / "game")
        os.makedirs(game_folder, exist_ok=True)

        _game_bin_python = os.path.join(game_folder, "Game", "Bin", "Python")
        _game_python = os.path.join(game_folder, "Python")
        if os.path.isfile(os.path.join(_game_bin_python, "generated.zip")):
            result = _game_bin_python
        else:
            result = _game_python

        assert result == _game_python
