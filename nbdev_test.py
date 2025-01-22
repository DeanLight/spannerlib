import subprocess
import os
from nbdev.doclinks import nbglob

files_to_test = nbglob()
files_to_skip = ['extended_version.ipynb']

for file in files_to_test:
    if os.path.basename(file) in files_to_skip:
        continue
    command = f"nbdev_test --path {file} --do_print"
    try:
        # Redirect stderr to stdout
        process = subprocess.Popen(command, shell=True, stderr=subprocess.STDOUT)
        process.wait()
    except subprocess.CalledProcessError as e:
        # An error occurred in the subprocess
        print(f"Error occurred while testing {file}: {e}")
    


