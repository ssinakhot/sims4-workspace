# decompyle3 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.0 (v3.7.0:1bf9cc5093, Jun 27 2018, 04:59:51) [MSC v.1914 64 bit (AMD64)]
# Embedded file name: G:\python scripting\Sims 4 Python Script Workspace (3.7)\Sims 4 Python Script Workspace\My Script Mods\TS4HeightSlider6_original\Scripts\injector.py
# Compiled at: 2018-11-16 08:03:56
# Size of source mod 2**32: 834 bytes
from functools import wraps
import inspect

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


def is_injectable(target_function, new_function):
    target_argspec = inspect.getfullargspec(target_function)
    new_argspec = inspect.getfullargspec(new_function)
    return len(target_argspec.args) == len(new_argspec.args) - 1
