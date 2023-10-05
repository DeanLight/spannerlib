import subprocess
from nbdev.doclinks import nbglob

files_to_test = nbglob()
processes = []

for file in files_to_test:
    command = f"nbdev_test --path {file} --do_print"
    try:
        process = subprocess.Popen(command, shell=True)
        processes.append(process)
    except Exception as e:
        print(f"Error occurred while testing {file}: {e}")

# Wait for all subprocesses to finish
for process in processes:
    # Get the output and error streams
    output, error = process.communicate()

    if process.returncode != 0:
        # An error occurred in the subprocess
        print(f"Error occurred while testing {file}: {error.decode('utf-8')}")

    process.wait()
