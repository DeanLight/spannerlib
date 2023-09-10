import functools

# This file is used for debugging purposes

def log_function_call(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"Calling function '{func.__name__}' with arguments:")
        if args:
            print(f"Positional arguments: {args}")
        if kwargs:
            print(f"Keyword arguments: {kwargs}")
        result = func(*args, **kwargs)
        print(f"Function '{func.__name__}' finished executing")
        return result
    return wrapper