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
from util.debug import install_debug_mod, remove_debug_mods
from util.watcher import watcher_create
from settings import mods_folder, src_path, creator_name, project_name, devmode_cmd_mod_src_path, devmode_cmd_mod_name

try:
    remove_debug_mods(mods_folder, creator_name + "_" + project_name)
    install_debug_mod(devmode_cmd_mod_src_path, mods_folder,
                      devmode_cmd_mod_name, creator_name + "_" + project_name)
    exec(open("sync_packages.py").read())
    watcher_create(creator_name, src_path, mods_folder, project_name)
except Exception as e:
    import traceback
    print(f"An error occurred: {str(e)}")
    print("Traceback:")
    traceback.print_exc()
