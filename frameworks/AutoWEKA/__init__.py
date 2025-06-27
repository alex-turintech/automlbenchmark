from amlb.utils import call_script_in_same_dir

_run_func = None  # Cache for imported run function

def setup(*args, **kwargs):
    call_script_in_same_dir(__file__, "setup.sh", *args, **kwargs)


def run(*args, **kwargs):
    global _run_func
    if _run_func is None:
        from .exec import run as _run_func
    return _run_func(*args, **kwargs)