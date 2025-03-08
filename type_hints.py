import multiprocessing, os

from Utility.helpers_type_hints import generate_type_hints, proto_type_hints, type_hints_pre
from settings import mods_folder, projects_python_path

if __name__ == "__main__":
    multiprocessing.freeze_support()

    type_hints_pre()

    if proto_type_hints(projects_python_path, os.path.join(projects_python_path, "proto"), mods_folder, "proto_finder"):
        generate_type_hints(projects_python_path)
