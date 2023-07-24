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

# Helpers
import multiprocessing

from Utility.helpers_decompile import decompile_pre, decompile_zips, decompile_print_totals

from Utility.helpers_path import ensure_path_created
from settings import gameplay_folder_data, gameplay_folder_game, projects_python_path

if __name__ == "__main__":
    multiprocessing.freeze_support()

    # Make sure the python folder exists
    ensure_path_created(projects_python_path)

    # Do a pre-setup
    decompile_pre()

    # Decompile all zips to the python projects folder
    print("")
    print("Beginning decompilation")
    print("This may take a while! Some files may not decompile properly which is normal.")
    print("")

    decompile_zips(gameplay_folder_data, projects_python_path)
    decompile_zips(gameplay_folder_game, projects_python_path)

    # Print final statistics
    decompile_print_totals()
