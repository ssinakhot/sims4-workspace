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

from subprocess import run, CompletedProcess, TimeoutExpired
import os.path, traceback
from typing import Tuple, Union
from Utility.helpers_path import get_sys_path, get_sys_scripts_folder, get_full_filepath

from settings import decompiler_timeout


def exec_cli(package: str, args: [str], **kwargs) -> Tuple[bool, Union[CompletedProcess, TimeoutExpired, None]]:
    """
    Executes the cli version of an installed python package

    :param package: Package name to execute
    :param args: Arguments to provide to the package
    :return: Returns tuple of (boolean indicating success, the CompletedProcess object)
    """
    # TODO: log stderr to a different file for each decompiler
    if os.path.isfile(package):
        cmd = package
    elif package == "python3":
        cmd = get_sys_path()
    else:
        cmd = get_full_filepath(get_sys_scripts_folder(), package)
    try:
        # TODO: make timeout scale with input file size?
        kwargs.setdefault("capture_output", True)
        kwargs.setdefault("timeout", decompiler_timeout)
        result = run([cmd, *args], text=True, encoding="utf-8", **kwargs)
    except TimeoutExpired as e:
        return False, e
    except Exception:
        traceback.print_exc()
        print(f"run was [{cmd}, {args}]")
        return False, None
    return (not str(result.stderr)) and (result.returncode == 0), result
