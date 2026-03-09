#    Copyright 2020 June Hanabi
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

# This installs, updates, and removes package files in the projects folder to match the assets folder
import fnmatch
import os
import shutil

from util.path import ensure_path_created, remove_file


def remove_tl_packages(path: str) -> int:
    count = 0

    # Remove existing package files
    for root, dirs, files in os.walk(path):
        for filename in fnmatch.filter(files, "*.package"):
            remove_file(root + os.sep + filename)
            count += 1

        # Only cover the top-level folder
        break
    return count


def copy_tl_packages(src: str, dest: str, file_list_failed: list) -> int:
    count = 0

    # Copy new assets
    for root, dirs, files in os.walk(src):
        for filename in files:
            if filename == ".gitkeep":
                continue
            try:
                shutil.copy(root + os.sep + filename,
                        dest + os.sep + filename)
                count += 1
            except Exception:
                file_list_failed.append(root + os.sep + filename)

        # Only cover the top-level folder
        break

    return count


def sync_packages(assets_path: str, mods_folder: str, build_path: str, creator_name: str, project_name: str) -> None:
    mod_name_folder_path = mods_folder + os.sep + creator_name + "_" + project_name

    ensure_path_created(mod_name_folder_path)
    file_list_failed = []

    files_removed = remove_tl_packages(mod_name_folder_path)
    remove_tl_packages(build_path)

    files_added = copy_tl_packages(assets_path, mod_name_folder_path, file_list_failed)
    copy_tl_packages(assets_path, build_path, file_list_failed)

    file_difference = files_added - files_removed

    print("Synced packages:" +
          " +" + str(files_added) +
          " -" + str(files_removed) +
          " ~" + str(file_difference))

    if len(file_list_failed) > 0:
        print("")
        print("Failed to copy these files, make sure the packages are named uniquely")
        print("")
        print("\n".join(file_list_failed))
