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
import contextlib, fnmatch, io, os, shutil, sys, tempfile, traceback
from multiprocessing import Pool
from pathlib import Path

# Helpers
from Utility.helpers_debug import install_debug_mod
from Utility.helpers_exec import exec_cli
from Utility.helpers_path import ensure_path_created, get_default_executable_extension, get_rel_path
from Utility.helpers_venv import Venv
from Utility.injector import inject, inject_to
from settings import num_threads

protoc_path = os.path.join(
    Path(__file__).resolve().parent.parent, "protoc", "protoc") + get_default_executable_extension()


def type_hints_pre() -> None:
    """
    Here we ensure needed packages are installed and install them if not
    We do this first because installation can create an error

    :return: Nothing
    """

    d = os.path.dirname(os.path.realpath(__file__))
    venv = Venv(os.path.join(d, "virtual_env"))
    venv.run()
    print("Checking for packages and installing if needed...")
    venv.install("six")
    venv.install("mypy")


def find_protos(src_dir: str, dst_dir: str) -> bool:
    """
    Generates a FileDescriptorSet containing every proto definition in the game.

    :param src_dir: Directory to search for protobuf _pb2.py files
    :param dst_dir: Directory to put proto data in
    :return: True iff the proto scanning worked
    """

    # TODO: try https://stackoverflow.com/questions/19418655/restoring-proto-file-from-descriptor-string-possible ?
    import importlib, os, pkgutil

    os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'
    os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION_VERSION'] = '2'

    sys.path.insert(1, os.path.join(src_dir, "generated"))
    # use our decompiled version of the game's own protobuf library - it's protobuf 2.4.1, so we can't even install it
    # on python 3.7 since its setup.py uses a no ( ) print statement
    sys.path.insert(1, os.path.join(src_dir, "core"))

    encoder_py = os.path.join(src_dir, "core", "google", "protobuf", "internal", "encoder.py")
    backup = encoder_py + '.backup'
    success: bool = False
    try:
        if os.path.exists(backup):
            shutil.copyfile(backup, encoder_py)
        else:
            shutil.copyfile(encoder_py, backup)
        # Replace all instances of " chr" in encoder.py with a bytes-returning version
        with open(encoder_py, 'r+') as file:
            encoder_py_contents = file.read()
            file.seek(0)
            file.write('import six\r\n' + encoder_py_contents.replace(' chr', ' six.int2byte'))
            file.truncate()

        import google.protobuf.internal.encoder
        import google.protobuf.internal.wire_format

        # Fix the StringEncoder not encoding the strings to bytes
        @inject_to(google.protobuf.internal.encoder, "StringEncoder")
        def on_string_encoder(original, field_number, is_repeated, is_packed):
            tag = google.protobuf.internal.encoder.TagBytes(
                field_number, google.protobuf.internal.wire_format.WIRETYPE_LENGTH_DELIMITED)
            local_encode_varint = google.protobuf.internal.encoder._EncodeVarint
            local_len = len

            encoder = original(field_number, is_repeated, is_packed)

            def fixed_encoder(orig2, write, value):
                if is_repeated:
                    for element in value:
                        encoded = element.encode('utf-8')
                        write(tag)
                        local_encode_varint(write, local_len(encoded))
                        write(encoded)
                else:
                    return orig2(write, value.encode('utf-8'))
            return inject(encoder, fixed_encoder)

        # Handle the bytes that EncodeVarint will now return
        @inject_to(google.protobuf.internal.encoder, "_VarintBytes")
        def on_varint_bytes(_original, value):
            pieces = []
            google.protobuf.internal.encoder._EncodeVarint(pieces.append, value)
            return b''.join(pieces)

        import google.protobuf.internal.python_message

        # Suppress the assertion errors caused by the game's version of protobuf not
        # having the fix for https://github.com/protocolbuffers/protobuf/issues/2533
        @inject_to(google.protobuf.internal.python_message, "_AddStaticMethods")
        def on_add_static_methods(original, cls):
            original(cls)
            orig2 = cls.RegisterExtension

            def on_register_extension(extension_handle):
                with contextlib.suppress(AssertionError):
                    return orig2(extension_handle)
            cls.RegisterExtension = on_register_extension

        # Use BytesIO instead of StringIO since all the encoders now write bytes
        @inject_to(google.protobuf.internal.python_message, "_AddSerializePartialToStringMethod")
        def on_add_static_methods(original, message_descriptor, cls):
            original(message_descriptor, cls)

            def on_serialize_partial_to_string(self):
                out = io.BytesIO()
                self._InternalSerialize(out.write)
                # counteract the .encode('latin-1') that SerializeToString will call
                return str(out.getvalue(), 'latin-1')
            cls.SerializePartialToString = on_serialize_partial_to_string

        import google.protobuf.descriptor_pb2

        # Set allow_alias when needed so that protoc > 2.4.1 can work
        # (we need the --descriptor_set_in flag which is a later addition)
        @inject_to(google.protobuf.descriptor_pb2.EnumDescriptorProto, "_InternalParse")
        def on_enum_internal_parse(original, self, buffer, pos, end):
            ret = original(self, buffer, pos, end)
            self.value: RepeatedCompositeFieldContainer
            val: google.protobuf.descriptor_pb2.EnumValueDescriptorProto
            seen = set()
            need_aa = False
            for val in self.value:
                val.number: int
                if val.number in seen:
                    need_aa = True
                    break
                seen.add(val.number)
            if need_aa:
                self.options: google.protobuf.descriptor_pb2.EnumOptions
                # set allow_alias = True for versions that actually understand it
                google.protobuf.descriptor._ParseOptions(self.options, '\020\001'.encode('latin1'))
            return ret

        # in protobuf after 2.4.1, extension fields are no longer allowed to be 'required'
        @inject_to(google.protobuf.descriptor_pb2.FieldDescriptorProto, "_InternalParse")
        def on_field_internal_parse(original, self, buffer, pos, end):
            self: google.protobuf.descriptor_pb2.FieldDescriptorProto
            ret = original(self, buffer, pos, end)
            if self.extendee != '' and self.label == self.LABEL_REQUIRED:
                self.label = self.LABEL_OPTIONAL
            return ret

        from google.protobuf import descriptor
        from google.protobuf.internal.containers import RepeatedCompositeFieldContainer

        fds = google.protobuf.descriptor_pb2.FileDescriptorSet()
        fds.file: RepeatedCompositeFieldContainer
        fds.file[-1]: google.protobuf.descriptor_pb2.FileDescriptorProto

        import protocolbuffers

        name: str
        for _, name, _ in pkgutil.walk_packages(google.__path__, google.__name__ + '.'):
            if not name.endswith('_pb2'):
                continue
            # print(name)
            module = importlib.import_module(name)
            fds.file.add()
            module.DESCRIPTOR: descriptor.FileDescriptor
            module.DESCRIPTOR.CopyToProto(fds.file[-1])
            if fds.file[-1].name == "":
                print(f"Failed to extract any data from serialized_pb: {fds.file[-1]}")
                return False
            # print(fds.file[-1])

        for _, name, _ in pkgutil.walk_packages(protocolbuffers.__path__, protocolbuffers.__name__ + "."):
            # print(name)
            module = importlib.import_module(name)
            fds.file.add()
            module.DESCRIPTOR: descriptor.FileDescriptor
            module.DESCRIPTOR.CopyToProto(fds.file[-1])
            if fds.file[-1].name == "":
                print(f"Failed to extract any data from serialized_pb: {fds.file[-1]}")
                return False
            # print(fds.file[-1])

        serialized: bytes = fds.SerializeToString()
        open(os.path.join(dst_dir, 'protos.txt'), 'w').write(str(fds))
        open(os.path.join(dst_dir, 'protos.pb'), 'wb').write(serialized)
        print("Protobuf FileDescriptorSet generated!")
        success = True
    finally:
        shutil.copyfile(backup, encoder_py)
        os.remove(backup)
    return success


def make_proto_finder(dst_dir: str, mods_dir: str, mod_folder_name: str) -> None:
    """
    Generates a mod that will generate a FileDescriptorSet on save load.

    :param dst_dir: Directory to put proto data in
    :param mods_dir: Path to the users mod folder
    :param mod_folder_name: Name of mod Subfolder
    :return: Nothing
    """

    script_template = f"""
import importlib, os, pkgutil
from functools import wraps


def inject(target_function, new_function):

    @wraps(target_function)
    def _inject(*args, **kwargs):
        return new_function(target_function, *args, **kwargs)

    return _inject


def inject_to(target_object, target_function_name):

    def _inject_to(new_function):
        target_function = getattr(target_object, target_function_name)
        setattr(target_object, target_function_name, inject(target_function, new_function))
        return new_function

    return _inject_to


import google, protocolbuffers
import google.protobuf.descriptor_pb2

# Set allow_alias when needed so that protoc > 2.4.1 can work
# (we need the --descriptor_set_in flag which is a later addition)
@inject_to(google.protobuf.descriptor_pb2.EnumDescriptorProto, "MergeFromString")
def on_internal_parse(original, self, serialized):
    ret = original(self, serialized)
    self.value: RepeatedCompositeFieldContainer
    val: google.protobuf.descriptor_pb2.EnumValueDescriptorProto
    seen = set()
    need_aa = False
    for val in self.value:
        val.number: int
        if val.number in seen:
            need_aa = True
            break
        seen.add(val.number)
    if need_aa:
        self.options: google.protobuf.descriptor_pb2.EnumOptions
        # set allow_alias = True for versions that actually understand it
        google.protobuf.descriptor._ParseOptions(self.options, ('\020\001').encode('latin1'))
    return ret


# in protobuf after 2.4.1, extension fields are no longer allowed to be 'required'
@inject_to(google.protobuf.descriptor_pb2.FieldDescriptorProto, "MergeFromString")
def on_field_internal_parse(original, self, serialized):
    self: google.protobuf.descriptor_pb2.FieldDescriptorProto
    ret = original(self, serialized)
    if self.extendee != '' and self.label == self.LABEL_REQUIRED:
        self.label = self.LABEL_OPTIONAL
    return ret


d = '{dst_dir}'
fds = google.protobuf.descriptor_pb2.FileDescriptorSet()

name: str
for _, name, _ in pkgutil.walk_packages(protocolbuffers.__path__, protocolbuffers.__name__ + "."):
    module = importlib.import_module(name)
    fds.file.add()
    module.DESCRIPTOR.CopyToProto(fds.file[-1])

for _, name, _ in pkgutil.walk_packages(google.__path__, google.__name__ + '.'):
    if not name.endswith('_pb2'):
        continue
    module = importlib.import_module(name)
    fds.file.add()
    module.DESCRIPTOR.CopyToProto(fds.file[-1])

open(os.path.join(d, 'inner_protos.txt'), 'w').write(str(fds))
open(os.path.join(d, 'inner_protos.pb'), 'wb').write(fds.SerializeToString())
"""

    with tempfile.TemporaryDirectory() as folder:
        script_path = os.path.join(folder, "proto_finder.py")
        with open(script_path, 'w') as file:
            file.write(script_template)
        install_debug_mod(script_path, mods_dir, "proto_finder", mod_folder_name)


def proto_type_hints(src_dir: str, dst_dir: str, mods_dir: str, mod_folder_name: str) -> bool:
    """
    Generates a FileDescriptorSet containing every proto definition in the game, or generates a mod
    that will do so.

    :param src_dir: Directory to search for protobuff _pb2.py files
    :param dst_dir: Directory to put proto data in
    :param mods_dir: Path to the users mod folder
    :param mod_folder_name: Name of mod Subfolder
    :return: True iff the proto scanning worked, False if the mod had to be generated
    """
    ensure_path_created(dst_dir)

    fds = os.path.join(dst_dir, 'protos.pb')
    have_fds = False
    try:
        if find_protos(src_dir, dst_dir):
            have_fds = True
    except (Exception, TypeError):
        print(traceback.format_exc())
    if not have_fds:
        have_fds = os.path.exists(fds) and os.stat(fds).st_size > 100
    if not have_fds:
        print("Failed to scan the proto definitions from outside, inserting a mod to do so...")
        make_proto_finder(dst_dir, mods_dir, mod_folder_name)
        return False
    else:
        if not os.path.isfile(protoc_path):
            print(f'Need a protoc executable at {protoc_path} to continue!')
            print('You can download one from https://github.com/protocolbuffers/protobuf/releases (need 3.20.0+)')
            return False
        stubs = os.path.abspath(os.path.join(dst_dir, '..', 'stubs'))
        ensure_path_created(stubs)
        did_anything: bool = False
        for root, dirs, files in os.walk(src_dir):
            base_pyi_path = os.path.join(stubs, get_rel_path(root, src_dir))
            any_pb2: bool = False
            all_pb2: bool = True

            for filename in files:
                if filename == '__init__.py':
                    continue
                if not filename.endswith('_pb2.py'):
                    all_pb2 = False
                    continue
                any_pb2 = True
                with open(os.path.join(root, filename), 'r', encoding='utf-8') as file:
                    line = 'not empty'
                    while line and not line.startswith('DESCRIPTOR'):
                        line = file.readline()
                    if line.startswith('DESCRIPTOR'):
                        proto_name = line.split("'")[1]
                    else:
                        proto_name = filename.replace("_pb2.py", ".proto")

                pyi_path = base_pyi_path
                proto_dir = os.path.normpath(os.path.dirname(proto_name))
                if proto_dir != '.':
                    if not pyi_path.endswith(proto_dir):
                        print(f'{pyi_path} vs {proto_dir}')
                        assert(pyi_path.endswith(proto_dir))
                    pyi_path = pyi_path[:-len(proto_dir)]

                ensure_path_created(pyi_path)
                success, result = exec_cli(
                    protoc_path, ["--descriptor_set_in", fds, '--pyi_out', pyi_path, proto_name])
                if not success:
                    print(protoc_path, ["--descriptor_set_in", fds, '--pyi_out', pyi_path, proto_name])
                    print(result.stderr)
                    all_pb2 = False
                    return False

            if all_pb2 and any_pb2:
                open(os.path.join(base_pyi_path, '__init__.pyi'), 'w').close()
            did_anything = True
        if did_anything:
            print("Stubs for all protobufs generated!")
        return did_anything


def type_hint_worker(src_file: str, dest_path: str):
    success, result = exec_cli("stubgen", ["-v", src_file, "-o", dest_path, "--include-private"])
    if not success:
        success, result = exec_cli("stubgen", ["-v", src_file, "-o", dest_path, "--include-private", "--parse-only"])
    if not success:
        print("stubgen", ["-v", src_file, "-o", dest_path, "--include-private", "--parse-only"])
        print(result.stderr)


def generate_type_hints(src_dir: str) -> bool:
    """
    Generates typehints for all python files in src_dir except protobuffs.

    :param src_dir: Directory to search for python files
    :return: True iff the proto scanning worked, False if the mod had to be generated
    """

    stubs = os.path.join(src_dir, 'stubs')
    ensure_path_created(stubs)

    sys.path.insert(1, os.path.join(src_dir, "base"))
    sys.path.insert(1, os.path.join(src_dir, "core"))
    sys.path.insert(1, os.path.join(src_dir, "generated"))
    sys.path.insert(1, os.path.join(src_dir, "simulation"))

    blacklist = ["generated", "proto", "stubs"]
    print("Using stubgen to generate python stubs! This will take a while!")

    # whether all the code in the src_dir can actually run
    all_code_can_run = False
    if all_code_can_run:
        from mypy.stubgen import parse_options, generate_stubs
        for scan in os.scandir(src_dir):
            if scan.is_dir():
                if scan.name in blacklist:
                    continue
                out = os.path.join(stubs, scan.name)
                # print("stubgen", ["-o", out, scan.path, "-v", "--include-private", "--ignore-errors"])
                options = parse_options(["-o", out, scan.path, "-v", "--include-private", "--ignore-errors"])
                try:
                    generate_stubs(options)
                except Exception:
                    pass
                # _success, _result = exec_cli("stubgen", ["-o", out, scan.path, "--include-private", "--ignore-errors"],
                #                              capture_output=False, timeout=None)
    else:
        work = []
        for root, dirs, files in os.walk(src_dir):
            if root.endswith("__pycache__"):
                continue
            base_pyi_path = os.path.join(stubs, get_rel_path(root, src_dir))

            for filename in fnmatch.filter(files, '*.py'):
                if filename.endswith("_pb2.py"):
                    continue
                filepath = os.path.join(root, filename)
                pyi_path = base_pyi_path
                out = os.path.join(pyi_path, filename.replace(".py", ".pyi"))
                if not os.path.exists(out):
                    while os.path.exists(os.path.join(pyi_path.replace(stubs, src_dir), "__init__.py")):
                        pyi_path = os.path.dirname(pyi_path)
                    # print(f'{filepath}, {pyi_path}')
                    work.append((filepath, pyi_path))
        with Pool(num_threads) as pool:
            pool.starmap(type_hint_worker, work)
    return True
