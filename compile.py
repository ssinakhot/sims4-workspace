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

from util.compile import compile_src
from util.sync_packages import sync_packages
from util.bundle_build import bundle_build
from settings import mods_folder, src_path, creator_name, build_path, project_name, assets_path
import traceback


def main():
    try:
        compile_src(creator_name, src_path, build_path, mods_folder, project_name)
        sync_packages(assets_path, mods_folder, build_path, creator_name, project_name)
        bundle_build(build_path, creator_name, project_name)
    except Exception as e:
        traceback.print_exc()


if __name__ == "__main__":
    main()
