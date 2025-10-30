import inspect

def debug(*args):
    """Print debug message with file and line number."""
    frame = inspect.currentframe().f_back
    filename = inspect.getfile(frame).split('\\')[-1]
    lineno = frame.f_lineno
    function_name = frame.f_code.co_name
    print(f"[DEBUG] {filename}:{lineno} ({function_name}) -", *args)
