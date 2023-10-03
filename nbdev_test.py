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
    process.wait()
