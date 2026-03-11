import os
import pytest

from util.datamining.package_discovery import (
    discover_simulation_packages,
    discover_string_packages,
    discover_client_packages,
    discover_all_packages,
)


def _touch(path):
    """Create an empty file, making parent dirs as needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        pass


def _make_game_folder(tmp_path):
    """Create a minimal game folder structure with mock .package files."""
    gf = str(tmp_path / "game")

    # Base game simulation
    _touch(os.path.join(gf, "Data", "Simulation", "SimulationFullBuild0.package"))
    _touch(os.path.join(gf, "Data", "Simulation", "SimulationDeltaBuild0.package"))

    # Base game client
    _touch(os.path.join(gf, "Data", "Client", "ClientFullBuild0.package"))
    _touch(os.path.join(gf, "Data", "Client", "ClientDeltaBuild0.package"))

    # Base game strings
    _touch(os.path.join(gf, "Data", "Client", "Strings_ENG_US.package"))

    # EP01 pack
    _touch(os.path.join(gf, "EP01", "SimulationFullBuild0.package"))
    _touch(os.path.join(gf, "EP01", "ClientFullBuild0.package"))
    _touch(os.path.join(gf, "EP01", "Strings_ENG_US.package"))

    # GP01 pack
    _touch(os.path.join(gf, "GP01", "SimulationFullBuild0.package"))
    _touch(os.path.join(gf, "GP01", "ClientFullBuild0.package"))

    # Delta for EP01
    _touch(os.path.join(gf, "Delta", "EP01", "SimulationDeltaBuild0.package"))
    _touch(os.path.join(gf, "Delta", "EP01", "ClientDeltaBuild0.package"))
    _touch(os.path.join(gf, "Delta", "EP01", "Strings_ENG_US.package"))

    return gf


class TestDiscoverSimulationPackages:
    def test_finds_all_packages(self, tmp_path):
        gf = _make_game_folder(tmp_path)
        pkgs = discover_simulation_packages(gf)
        assert len(pkgs) == 5  # 3 full + 2 delta

    def test_full_before_delta(self, tmp_path):
        gf = _make_game_folder(tmp_path)
        pkgs = discover_simulation_packages(gf)
        rels = [rel for _, rel in pkgs]

        # All full builds should come before any delta builds
        full_indices = [i for i, r in enumerate(rels) if "Full" in r]
        delta_indices = [i for i, r in enumerate(rels) if "Delta" in r]
        assert max(full_indices) < min(delta_indices)

    def test_returns_tuples(self, tmp_path):
        gf = _make_game_folder(tmp_path)
        pkgs = discover_simulation_packages(gf)
        for abs_path, rel_path in pkgs:
            assert os.path.isabs(abs_path)
            assert not os.path.isabs(rel_path)

    def test_relative_paths(self, tmp_path):
        gf = _make_game_folder(tmp_path)
        pkgs = discover_simulation_packages(gf)
        rels = [rel for _, rel in pkgs]
        assert "Data/Simulation/SimulationFullBuild0.package" in rels
        assert "EP01/SimulationFullBuild0.package" in rels
        assert "Delta/EP01/SimulationDeltaBuild0.package" in rels

    def test_empty_folder(self, tmp_path):
        gf = str(tmp_path / "empty")
        os.makedirs(gf)
        assert discover_simulation_packages(gf) == []

    def test_missing_folder(self, tmp_path):
        gf = str(tmp_path / "nonexistent")
        assert discover_simulation_packages(gf) == []


class TestDiscoverStringPackages:
    def test_finds_all_string_packages(self, tmp_path):
        gf = _make_game_folder(tmp_path)
        pkgs = discover_string_packages(gf)
        assert len(pkgs) == 3  # base + EP01 + Delta/EP01

    def test_base_first(self, tmp_path):
        gf = _make_game_folder(tmp_path)
        pkgs = discover_string_packages(gf)
        assert "Strings_ENG_US" in os.path.basename(pkgs[0])
        assert "Data" in pkgs[0]

    def test_empty_folder(self, tmp_path):
        gf = str(tmp_path / "empty")
        os.makedirs(gf)
        assert discover_string_packages(gf) == []


class TestDiscoverClientPackages:
    def test_finds_all_client_packages(self, tmp_path):
        gf = _make_game_folder(tmp_path)
        pkgs = discover_client_packages(gf)
        assert len(pkgs) == 5  # 3 full + 2 delta

    def test_full_before_delta(self, tmp_path):
        gf = _make_game_folder(tmp_path)
        pkgs = discover_client_packages(gf)
        rels = [rel for _, rel in pkgs]

        full_indices = [i for i, r in enumerate(rels) if "Full" in r]
        delta_indices = [i for i, r in enumerate(rels) if "Delta" in r]
        assert max(full_indices) < min(delta_indices)

    def test_empty_folder(self, tmp_path):
        gf = str(tmp_path / "empty")
        os.makedirs(gf)
        assert discover_client_packages(gf) == []


class TestDiscoverAllPackages:
    def test_finds_everything(self, tmp_path):
        gf = _make_game_folder(tmp_path)
        pkgs = discover_all_packages(gf)
        # Should find all .package files regardless of name
        assert len(pkgs) >= 10  # at least all the ones we created

    def test_returns_relative_paths(self, tmp_path):
        gf = _make_game_folder(tmp_path)
        pkgs = discover_all_packages(gf)
        for abs_path, rel_path in pkgs:
            assert os.path.isabs(abs_path)
            assert not os.path.isabs(rel_path)
            assert os.path.isfile(abs_path)
