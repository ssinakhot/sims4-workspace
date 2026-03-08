# Post-Refactor Verification Checklist

Run these checks after setting up the project (with `settings.py` configured):

1. `python compile.py` — verify same compile + sync + bundle behavior
2. `python devmode.py` — verify watcher starts and syncs packages
3. `python sync_packages.py` — verify standalone sync still works
4. `python bundle_build.py` — verify standalone bundle still works
5. `python cleanup.py` — verify cleanup works
6. `python debug_setup.py` — verify debug setup works
7. `python debug_teardown.py` — verify debug teardown works
8. `python decompile.py --folder` — verify decompilation from folder
9. `python decompile.py --game` — verify game decompilation
10. `python datamine.py --help` — verify CLI shows subcommands
11. `pytest -v` — all tests pass
12. Rebuild devcontainer — verify `.devcontainer/post-create.sh` runs from new location
