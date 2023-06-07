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
import contextlib, os, shutil, tempfile
from settings import build_path, creator_name, project_name
from Utility.helpers_path import ensure_path_created, get_rel_path, remove_file
from zipfile import PyZipFile, ZIP_STORED

# Build paths and create temp directory
folder_name = creator_name + "_" + project_name
bundle_path = build_path + os.sep + folder_name + ".zip"
tmp_dir = tempfile.TemporaryDirectory()
tmp_dst_path = tmp_dir.name + os.sep + folder_name

# Ensure build directory is created
ensure_path_created(build_path)

# Remove existing bundle
remove_file(bundle_path)

# Copy build files to tmp dir
shutil.copytree(build_path, tmp_dst_path)

# Zip up bundled folder
zf = PyZipFile(bundle_path, mode='w', compression=ZIP_STORED, allowZip64=True, optimize=2)
for root, dirs, files in os.walk(tmp_dir.name):
    for filename in files:
        rel_path = get_rel_path(root + os.sep + filename, tmp_dir.name)
        zf.write(root + os.sep + filename, rel_path)
zf.close()

# There's a temporary directory bug that causes auto-cleanup to sometimes fail
# We're preventing crash messages from flooding the screen to keep things tidy
with contextlib.suppress(Exception):
    tmp_dir.cleanup()

print("Created final mod zip at: " + "build" + os.sep + folder_name + ".zip")
