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

import fnmatch
import os

from settings import projects_tuning_path

# For pretty progress and results
col_count = 0
suc_count = 0
fail_count = 0
skip_count = 0
count = 0

failed_filename_list = []


def loop_end() -> None:
    global count
    global col_count

    count += 1
    col_count += 1
    if col_count >= 80:
        col_count = 0
        print("")


def attempt_rename(from_path: str, to_folder: str, to_file_stem: str) -> None:
    # Suffixes to append to the filename, in order, when a rename fails
    attempts = ['', '_a', '_b', '_c', '_d']

    success = False

    for attempt in attempts:
        try:
            os.rename(from_path, to_folder + os.sep + to_file_stem + attempt + ".xml")
            success = True
            break
        except:
            pass

    if not success:
        raise NameError("Failed to rename file")


def begin_fix() -> None:
    global suc_count
    global fail_count
    global skip_count
    global failed_filename_list

    print("Fixing filenames...")
    print("")

    for folder, subs, files in os.walk(projects_tuning_path):
        for filename in fnmatch.filter(files, '*.xml'):

            new_filename = filename.split(".")

            if len(new_filename) <= 2:
                print("_", end="")
                skip_count += 1
                loop_end()
                continue

            new_filename.pop(0)
            new_filename.pop()
            new_filename.pop()
            new_filename = "_".join(new_filename)

            try:
                attempt_rename(folder + os.sep + filename, folder, new_filename)
                print(".", end="")
                suc_count += 1
            except:
                print("x", end="")
                fail_count += 1
                failed_filename_list.append(folder + os.sep + filename)

            loop_end()

    print("")
    print("")
    print("Completed")
    print("S: " + str(suc_count) + " [" + str(round((suc_count/count) * 100, 2)) + "%], ", end="")
    print("F: " + str(fail_count) + " [" + str(round((fail_count/count) * 100, 2)) + "%], ", end="")
    print("X: " + str(skip_count) + " [" + str(round((skip_count / count) * 100, 2)) + "%], ", end="")
    print("T: " + str(count))

    if len(failed_filename_list) > 0:
        print("")
        print("Failed to rename files:")
        print("")
        print("\n".join(failed_filename_list))
        print("")


def main():
    print("This requires using Sims 4 Studio to export all Tuning files using sub-folders at the currently")
    print("configured location: " + projects_tuning_path)
    answer = input("Have you done this? [y/n]: ")

    if answer == "y":
        begin_fix()


if __name__ == "__main__":
    main()
