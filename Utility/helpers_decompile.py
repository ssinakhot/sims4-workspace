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

# core imports
import os
import fnmatch
import shutil
import tempfile
import traceback
from multiprocessing import Pool
from zipfile import PyZipFile
from pathlib import Path

from multiprocessing.sharedctypes import Value
from ctypes import Structure, c_uint

# Helpers
from Utility.helpers_path import replace_extension, get_rel_path, get_file_stem, ensure_path_created
from Utility.helpers_package import install_package, exec_package
from Utility.helpers_time import get_time, get_time_str, get_minutes
from Utility import process_module
from settings import num_decompilers

# Globals
script_package_types = ['*.zip', '*.ts4script']
python_compiled_ext = "*.pyc"


class Stats(Structure):
    _fields_ = [('suc_count', c_uint), ('fail_count', c_uint), ('count', c_uint), ('col_count', c_uint)]


class TotalStats(Structure):
    _fields_ = [('suc_count', c_uint), ('fail_count', c_uint), ('count', c_uint), ('minutes', c_uint)]


# Global counts and timings for all the tasks
totals = Value(TotalStats, 0, 0, 0, 0)
# TODO: report infinite loop errors to https://github.com/greyblue9/unpyc37-3.10
unpyc3_path = os.path.realpath(os.path.join(__file__, "..", "..", "unpyc37", "unpyc3.py"))


def decompile_pre() -> None:
    """
    Here we ensure our decompilers are installed and install them if not
    We do this first because installation can create an error

    :return: Nothing
    """

    print("Checking for decompilers and installing if needed...")
    install_package("decompyle3")
    assert (os.path.isfile(unpyc3_path))
    install_package("uncompyle6")


def print_progress(stats: Stats, total: TotalStats, success: bool):
    # Print progress
    # Prints a single dot on the same line which gives a nice clean progress report
    # Tally number of files and successful / failed files
    if success:
        print(".", end="")
        stats.suc_count += 1
        total.suc_count += 1
    else:
        print("x", end="")
        stats.fail_count += 1
        total.fail_count += 1

    stats.count += 1
    total.count += 1

    # Insert a new progress line every 80 characters
    stats.col_count += 1
    if stats.col_count >= 80:
        stats.col_count = 0
        print("")


def print_summary(stats: Stats):
    print(f"S: {stats.suc_count} [{round((stats.suc_count / stats.count) * 100, 2)}%], ", end="")
    print(f"F: {stats.fail_count} [{round((stats.fail_count / stats.count) * 100, 2)}%], ", end="")
    print(f"T: {stats.count}, ", end="")


def unpyc3_helper(cmd: str, args: [str], dest_path: str) -> bool:
    success, result = exec_package(cmd, args)
    if success:
        try:
            with open(dest_path, "w", encoding="utf-8") as file:
                file.write(result.stdout)
        except Exception as e:
            traceback.print_exc()
            print(f"command was {cmd}, {args}, {dest_path}")
            success = False
    return success


def decompile_worker(dest_path: str, src_file: str):
    # TODO: if none are completely successful, keep whichever decompilation resulted in the most lines of real code
    success, _ = exec_package("decompyle3", ["-o", dest_path, src_file])
    if not success:
        success = unpyc3_helper("python3", [unpyc3_path, src_file], dest_path)
    # TODO: also try https://github.com/zrax/pycdc
    if not success:
        success, _ = exec_package("uncompyle6", ["-o", dest_path, src_file])
    print_progress(process_module.stats, process_module.total_stats, success)


# I don't fully understand why this is necessary, but thanks to https://stackoverflow.com/a/1721911
def init_process(stats, total):
    process_module.stats = stats
    process_module.total_stats = total


def decompile_dir(src_dir: str, dest_dir: str, zip_name: str) -> None:
    """
    Decompiles a directory of compiled python files to a different directory
    Modified from andrew's code.
    https://sims4studio.com/thread/15145/started-python-scripting

    :param src_dir: Path of dir to decompile
    :param dest_dir: Path of dir to send decompiled files to
    :param zip_name: Original filename of what's being decompiled (For progress output purposes)
    :return: Nothing
    """

    # Begin clock
    time_start = get_time()

    print("Decompiling " + zip_name)

    # Local counts for this one task
    task_stats = Value(Stats, 0, 0, 0, 0)

    to_decompile = []

    # Go through each compiled python file in the folder
    for root, dirs, files in os.walk(src_dir):
        for filename in fnmatch.filter(files, python_compiled_ext):

            # Get details about the source file
            src_file = str(os.path.join(root, filename))
            src_file_rel_path = get_rel_path(src_file, src_dir)

            # Create destination file path
            dest_path = replace_extension(dest_dir + os.path.sep + src_file_rel_path, "py")

            # And ensures the folders exist so there's no error
            # Make sure to strip off the file name at the end
            ensure_path_created(str(Path(dest_path).parent))

            to_decompile.append((dest_path, src_file))

    with Pool(num_decompilers, init_process, (task_stats, totals)) as pool:
        pool.starmap(decompile_worker, to_decompile)

    time_end = get_time()
    elapsed_minutes = get_minutes(time_end, time_start)
    totals.minutes += elapsed_minutes

    # Print a newline and then a compact completion message giving successful, failed, and total count stats and timing
    print("")
    print("")
    print("Completed")
    print_summary(task_stats)
    print(get_time_str(elapsed_minutes))
    print("")


def decompile_zip(src_dir: str, zip_name: str, dst_dir: str) -> None:
    """
    Copies a zip file to a temporary folder, extracts it, and then decompiles it to the projects folder
    Modified from andrew's code.
    https://sims4studio.com/thread/15145/started-python-scripting

    :param src_dir: Source directory for zip file
    :param zip_name: zip filename
    :param dst_dir: Destination for unzipped files
    :return: Nothing
    """

    # Create paths and directories
    file_stem = get_file_stem(zip_name)

    src_zip = os.path.join(src_dir, zip_name)
    dst_dir = os.path.join(dst_dir, file_stem)

    tmp_dir = tempfile.TemporaryDirectory()
    tmp_zip = os.path.join(tmp_dir.name, zip_name)

    # Copy zip to temp path
    shutil.copyfile(src_zip, tmp_zip)

    # Grab handle to zip file and extract all contents to the same folder
    zip_file = PyZipFile(tmp_zip)
    zip_file.extractall(tmp_dir.name)

    # Decompile the directory
    decompile_dir(tmp_dir.name, dst_dir, zip_name)

    # There's a temporary directory bug that causes auto-cleanup to sometimes fail
    # We're preventing crash messages from flooding the screen to keep things tidy
    try:
        tmp_dir.cleanup()
    except:
        pass


def decompile_zips(src_dir: str, dst_dir: str) -> None:
    """
    Decompiles a folder of zip files to a destination folder
    Modified from andrew's code.
    https://sims4studio.com/thread/15145/started-python-scripting

    :param src_dir: Directory to search for and decompile zip files
    :param dst_dir: Directory to send decompiled files to
    :return: Nothing
    """
    for root, dirs, files in os.walk(src_dir):
        for ext_filter in script_package_types:
            for filename in fnmatch.filter(files, ext_filter):
                decompile_zip(root, filename, dst_dir)


def decompile_print_totals() -> None:
    print("Results")

    # Fix Bug #1
    # https://github.com/junebug12851/Sims4ScriptingBPProj/issues/1
    try:
        print(f"S: {totals.suc_count} [{round((totals.suc_count / totals.count) * 100, 2)}%], ", end="")
        print(f"F: {totals.fail_count} [{round((totals.fail_count / totals.count) * 100, 2)}%], ", end="")
        print(f"T: {totals.count}, ", end="")
        print(get_time_str(totals.minutes))
    except:
        print("No files were processed, an error has occurred. Is the path to the game folder correct?")
        pass

    print("")
