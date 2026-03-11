"""
Discover game .package files organized by category.

Consolidates the package discovery logic used by extraction scripts
into a single reusable module.
"""

import glob
import os
from typing import List, Tuple


# Pack directory prefixes (expansion, game, stuff, free packs)
_PACK_PATTERNS = ("EP*", "GP*", "SP*", "FP*")


def _find_sorted(pattern):
    # type: (str) -> List[str]
    """Glob and sort results for deterministic ordering."""
    return sorted(glob.glob(pattern))


def discover_simulation_packages(game_folder):
    # type: (str) -> List[Tuple[str, str]]
    """Find all simulation .package files, ordered full-before-delta.

    Returns list of (absolute_path, relative_path) tuples.
    Full builds come first so delta builds can override during deduplication.
    """
    packages = []  # type: List[Tuple[str, str]]

    # --- Full builds first ---
    sim_dir = os.path.join(game_folder, "Data", "Simulation")
    full_path = os.path.join(sim_dir, "SimulationFullBuild0.package")
    if os.path.isfile(full_path):
        packages.append((full_path, "Data/Simulation/SimulationFullBuild0.package"))

    for pattern in _PACK_PATTERNS:
        for pack_dir in _find_sorted(os.path.join(game_folder, pattern)):
            pkg = os.path.join(pack_dir, "SimulationFullBuild0.package")
            if os.path.isfile(pkg):
                rel = os.path.basename(pack_dir) + "/SimulationFullBuild0.package"
                packages.append((pkg, rel))

    # --- Delta builds second ---
    delta_path = os.path.join(sim_dir, "SimulationDeltaBuild0.package")
    if os.path.isfile(delta_path):
        packages.append((delta_path, "Data/Simulation/SimulationDeltaBuild0.package"))

    delta_dir = os.path.join(game_folder, "Delta")
    if os.path.isdir(delta_dir):
        for pattern in _PACK_PATTERNS:
            for pack_dir in _find_sorted(os.path.join(delta_dir, pattern)):
                pkg = os.path.join(pack_dir, "SimulationDeltaBuild0.package")
                if os.path.isfile(pkg):
                    rel = "Delta/" + os.path.basename(pack_dir) + "/SimulationDeltaBuild0.package"
                    packages.append((pkg, rel))

    return packages


def discover_string_packages(game_folder):
    # type: (str) -> List[str]
    """Find all Strings_ENG_US.package files.

    Returns list of absolute paths. Base + pack strings first, then deltas.
    """
    packages = []  # type: List[str]

    # Base game strings
    base = os.path.join(game_folder, "Data", "Client", "Strings_ENG_US.package")
    if os.path.isfile(base):
        packages.append(base)

    # Pack strings
    for pattern in _PACK_PATTERNS:
        for pack_dir in _find_sorted(os.path.join(game_folder, pattern)):
            pkg = os.path.join(pack_dir, "Strings_ENG_US.package")
            if os.path.isfile(pkg):
                packages.append(pkg)

    # Delta strings
    delta_dir = os.path.join(game_folder, "Delta")
    if os.path.isdir(delta_dir):
        for pattern in _PACK_PATTERNS:
            for pack_dir in _find_sorted(os.path.join(delta_dir, pattern)):
                pkg = os.path.join(pack_dir, "Strings_ENG_US.package")
                if os.path.isfile(pkg):
                    packages.append(pkg)

    return packages


def discover_client_packages(game_folder):
    # type: (str) -> List[Tuple[str, str]]
    """Find all Client*Build*.package files, ordered full-before-delta.

    Returns list of (absolute_path, relative_path) tuples.
    Full builds come first so delta builds can override during deduplication.
    """
    packages = []  # type: List[Tuple[str, str]]

    # --- Full builds first ---
    client_dir = os.path.join(game_folder, "Data", "Client")
    for pkg in _find_sorted(os.path.join(client_dir, "ClientFullBuild*.package")):
        rel = "Data/Client/" + os.path.basename(pkg)
        packages.append((pkg, rel))

    for pattern in _PACK_PATTERNS:
        for pack_dir in _find_sorted(os.path.join(game_folder, pattern)):
            for pkg in _find_sorted(os.path.join(pack_dir, "ClientFullBuild*.package")):
                rel = os.path.basename(pack_dir) + "/" + os.path.basename(pkg)
                packages.append((pkg, rel))

    # --- Delta builds second ---
    for pkg in _find_sorted(os.path.join(client_dir, "ClientDeltaBuild*.package")):
        rel = "Data/Client/" + os.path.basename(pkg)
        packages.append((pkg, rel))

    delta_dir = os.path.join(game_folder, "Delta")
    if os.path.isdir(delta_dir):
        for pattern in _PACK_PATTERNS:
            for pack_dir in _find_sorted(os.path.join(delta_dir, pattern)):
                for pkg in _find_sorted(os.path.join(pack_dir, "ClientDeltaBuild*.package")):
                    rel = "Delta/" + os.path.basename(pack_dir) + "/" + os.path.basename(pkg)
                    packages.append((pkg, rel))

    return packages


def discover_all_packages(game_folder):
    # type: (str) -> List[Tuple[str, str]]
    """Find all .package files under the game folder.

    Returns list of (absolute_path, relative_path) tuples.
    Walks the entire directory tree.
    """
    packages = []  # type: List[Tuple[str, str]]
    for root, dirs, files in os.walk(game_folder):
        dirs.sort()  # deterministic ordering
        for f in sorted(files):
            if f.endswith(".package"):
                abs_path = os.path.join(root, f)
                rel_path = os.path.relpath(abs_path, game_folder)
                packages.append((abs_path, rel_path))
    return packages
