import tempfile
import shutil
import os
import time
import functools
from cloney.logger import logging


def create_temp_directory():
    temp_dir = tempfile.mkdtemp()
    return temp_dir

def cleanup_temp_directory(temp_dir):
    shutil.rmtree(temp_dir)

def time_logger(func):
    @functools.wraps(func)  # Preserve original function name and docstring
    def wrapper(*args, **kwargs):
        start_time = time.time()
        logging.info(f"Function '{func.__name__}' Started....")
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        logging.info(f"Function '{func.__name__}' Ended....")
        logging.info(f"Function '{func.__name__}' executed in {elapsed_time:.6f} seconds")
        return result
    return wrapper