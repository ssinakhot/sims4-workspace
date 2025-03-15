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
from util.path import remove_dir, ensure_path_created
from pathlib import Path

import os
from subprocess import run
import shutil
import time
from threading import Thread


def get_scripts_path(creator_name: str, mods_dir: str, mod_name: str = "Untitled") -> str:
    """
    This builds a path to the Scripts folder inside the Mod Folder

    :param creator_name: Creator Name
    :param mods_dir: Path to the Mods Folder
    :param mod_name: Name of Mod
    :return: Path to Scripts folder inside Mod Name Folder
    """

    # creator_name can be omitted, if it's not then prefix it
    if creator_name:
        mod_name = creator_name + '_' + mod_name

    # Build absolute path to mod name folder
    mods_sub_dir = os.path.join(mods_dir, mod_name)

    # Return path to Scripts folder inside Mod name Folder
    return os.path.join(mods_sub_dir, "Scripts")


def exec_cmd(cmd: str, args: str) -> bool:
    """
    This executes a system command and returns whether it was successful or not

    :param cmd: Command to execute
    :param args: Any arguments to command
    :return: Successful or not
    """

    # Result object of the command
    # If an error occurs, this will be the value used
    result = None

    try:
        # Run the command and capture output
        result = run(cmd + " " + args,
                     capture_output=True,
                     text=True,
                     shell=True)
    except:
        pass

    # If the command completely crashed then return false
    if result is None:
        return False

    # Otherwise return false if stderr contains error messages and/or the return code is not 0
    return (not str(result.stderr)) and (result.returncode == 0)


def watcher_folder_exists(creator_name: str, mods_dir: str, mod_name: str = "Untitled") -> bool:
    """
    Checks to see if a Scripts folder or file exists inside the Mod Folder

    :param creator_name: Creator Name
    :param mods_dir: Path to the Mods Folder
    :param mod_name: Name of Mod
    :return: Whether a "Scripts" file or folder does exist in the Mod Folder
    """

    scripts_path = get_scripts_path(creator_name, mods_dir, mod_name)
    return os.path.exists(scripts_path)


def watcher_folder_remove(creator_name: str, mods_dir: str, mod_name: str = "Untitled") -> None:
    """
    Safely removes /Mods/ModName/Scripts

    :param creator_name: Creator Name
    :param mods_dir: Path to the Mods Folder
    :param mod_name: Name of Mod
    :param remove_whole_dir: whether to really remove the whole Mod Name folder vs just the symlink inside it
    :return: Nothing
    """

    # Build paths
    scripts_path = get_scripts_path(creator_name, mods_dir, mod_name)
    mod_folder_path = str(Path(scripts_path).parent)

    # Check whether the Scripts folder exists
    exists = watcher_folder_exists(creator_name, mods_dir, mod_name)

    # Delete the Scripts folder and check whether it was successful
    # Try to use Python's built-in functions first, then fall back to system command
    if exists:
        try:
            if os.path.isdir(scripts_path):
                if os.path.islink(scripts_path) or os.path.ismount(scripts_path):
                    os.rmdir(scripts_path)
                else:
                    shutil.rmtree(scripts_path)
            elif os.path.isfile(scripts_path):
                os.remove(scripts_path)
        except Exception as e:
            print(f"Error removing {scripts_path}: {e}")
            # Fall back to system command
            success = exec_cmd("rmdir", '"' + scripts_path + '"')


def watcher_create(creator_name: str, src_dir: str, mods_dir: str, mod_name: str = "Untitled") -> None:
    """
    Creates a live file watcher that copies files from source to the game's mod directory.
    
    This function first removes any existing mod files, then sets up continuous monitoring
    of the source directory. When changes are detected, files are automatically copied
    to the destination, enabling real-time development without manual compilation.

    :param creator_name: Creator Name used as prefix for the mod folder
    :param src_dir: Path to the source directory containing development files
    :param mods_dir: Path to the game's Mods directory
    :param mod_name: Name of the mod folder (defaults to "Untitled")
    :return: Nothing, runs until interrupted with Ctrl+C
    """

    # Build paths
    scripts_path = get_scripts_path(creator_name, mods_dir, mod_name)

    # Safely remove the watcher folder
    watcher_folder_remove(creator_name, mods_dir, mod_name)

    # Ensure parent directory exists
    mod_folder_path = str(Path(scripts_path).parent)
    ensure_path_created(mod_folder_path)

    print("")
    print("Dev Mode is activated, you no longer have to compile after each change, run devmode.reload [path.of.module]")
    print("to reload individual files while the game is running. To exit dev mode, simply run 'compile.py' which will")
    print("return things to normal.")
    print("It's recommended to test a compiled version before final release after working in Dev Mode")
    print("")

    # First copy the files from source to destination
    shutil.copytree(src_dir, scripts_path)
    
    # Define a function to periodically copy files
    def update_files():
        try:
            # Get list of files in source directory
            for root, dirs, files in os.walk(src_dir):
                # Get relative path
                rel_path = os.path.relpath(root, src_dir)
                # Create destination directory if it doesn't exist
                dest_dir = os.path.join(scripts_path, rel_path) if rel_path != '.' else scripts_path
                os.makedirs(dest_dir, exist_ok=True)
                
                # Copy each file only if it's been modified
                for file in files:
                    src_file = os.path.join(root, file)
                    dest_file = os.path.join(dest_dir, file)
                    
                    # Check if destination file exists and compare modification times
                    try:
                        if not os.path.exists(dest_file) or int(os.path.getmtime(src_file)) > int(os.path.getmtime(dest_file)):
                            shutil.copy2(src_file, dest_file)
                            now = time.strftime("%H:%M:%S")
                            print(f"[{now}] Updated file: {src_file}")
                    except (OSError, FileNotFoundError) as e:
                        # Handle file access errors
                        print(f"Error checking file timestamps for {src_file}: {e}")
                        # Force copy if there was an error checking timestamps
                        shutil.copy2(src_file, dest_file)
                        now = time.strftime("%H:%M:%S")
                        change = True
            
        except Exception as e:
            print(f"Error during update: {e}")
    
    # Initial copy
    update_files()
    
    # Start a background thread to continuously update the files
    def auto_update_thread():
        while True:
            try:
                time.sleep(1)
                update_files()
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error in update thread: {e}")
                time.sleep(5)  # Wait before retrying
    
    # Create and start the thread
    update_thread = Thread(target=auto_update_thread, daemon=True)
    update_thread.start()
    
    print("Auto-update thread started. Files will be copied whenever you update them.")
    print("Press Ctrl+C to stop the script when you're done.")

    # Keep the main thread alive to allow the daemon thread to run
    try:
        # Keep the main thread running until interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        watcher_folder_remove(creator_name, mods_dir, mod_name)
        print("\nStopping auto-update.")


