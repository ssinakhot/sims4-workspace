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
import argparse

from Utility.helpers_decompile import decompile_pre, decompile_zips, decompile_print_totals
from settings import gameplay_folder_data, gameplay_folder_game 

if __name__ == "__main__":
    multiprocessing.freeze_support()

    parser = argparse.ArgumentParser(description="Decompile script")
    parser.add_argument('--folder', action='store_true', help="Decompile all files in the decompile folder")
    parser.add_argument('--game', action='store_true', help="Decompile game files")
    args = parser.parse_args()

    if not args.folder and not args.game:
        parser.print_help()
        exit(1)

    # Do a pre-setup
    decompile_pre()

    # Decompile all zips to the python projects folder
    print("")
    print("Beginning decompilation")
    print("This may take a while! Some files may not decompile properly which is normal.")
    print("")

    decompile_output_folder = "./decompile/output"

    if args.folder:
        decompile_zips("./decompile/input", decompile_output_folder)
    elif args.game:
        decompile_zips(gameplay_folder_data, decompile_output_folder)
        decompile_zips(gameplay_folder_game, decompile_output_folder)

    # Print final statistics
    decompile_print_totals()
