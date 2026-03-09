import os, subprocess, sys, venv


# Inspired by https://stackoverflow.com/a/57604352/7376471, but using the built-in "venv" package instead
class Venv:
    def __init__(self, virtual_dir):
        self.virtual_dir = virtual_dir
        if os.name == 'nt':
            self.virtual_python = os.path.join(self.virtual_dir, "Scripts", "python.exe")
        else:
            self.virtual_python = os.path.join(self.virtual_dir, "bin", "python")

    def _has_pip(self):
        result = subprocess.call(
            [self.virtual_python, "-m", "pip", "--version"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return result == 0

    def _ensure_pip(self):
        if not self._has_pip():
            print("pip not found in venv, bootstrapping with ensurepip...")
            subprocess.call([self.virtual_python, "-m", "ensurepip"])

    def install_virtual_env(self):
        if not os.path.exists(self.virtual_python):
            build = venv.EnvBuilder(symlinks=True, upgrade=True, with_pip=True)
            build.create(self.virtual_dir)
            print("created virtual environment: " + self.virtual_dir)
        else:
            print("found virtual python: " + self.virtual_python)
        self._ensure_pip()

    def is_venv(self):
        return sys.prefix==self.virtual_dir

    def restart_under_venv(self):
        print("Restarting under virtual environment " + self.virtual_dir + ", " + __file__)
        subprocess.call([self.virtual_python] + sys.argv)
        exit(0)

    def install(self, package):
        os.environ["PIP_REQUIRE_VIRTUALENV"] = "true"
        subprocess.call([self.virtual_python, "-m", "pip", "install", package, "--upgrade"])

    def run(self):
        if not self.is_venv():
            self.install_virtual_env()
            self.restart_under_venv()
        else:
            print("Running under virtual environment")
            self.install("pip")
