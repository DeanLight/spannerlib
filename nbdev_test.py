import subprocess
from nbdev.doclinks import nbglob

files_to_test = nbglob()
processes = []

for file in files_to_test:
    command = f"nbdev_test --path {file} --do_print"
    try:
        # Redirect stderr to stdout
        process = subprocess.Popen(command, shell=True, stderr=subprocess.STDOUT)
        processes.append(process)
    except subprocess.CalledProcessError as e:
        # An error occurred in the subprocess
        print(f"Error occurred while testing {file}: {e}")

# Wait for all subprocesses to finish
for process in processes:
    process.wait()
