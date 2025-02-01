import tempfile
import shutil
import os

def create_temp_directory():
    temp_dir = tempfile.mkdtemp()
    return temp_dir

def cleanup_temp_directory(temp_dir):
    shutil.rmtree(temp_dir)
