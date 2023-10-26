import inspect
from nbdev.processors import FilterDefaults
from nbdev.quarto import nbdev_docs

monkey_patch_procs = """
# already_appended_marker
all_procs = FilterDefaults().procs()
def new_procs(self):
    procs = [proc for proc in all_procs if proc.__name__ != 'clean_magics']
    return procs
FilterDefaults.procs = new_procs
"""

def check_appeneded_marker(file_path # Path to nbdev.processors.py file
                           ) -> bool: # True if we already appended new_procs, False otherwise
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()

            for line in lines:
                if 'already_appended_marker' in line:
                    return True
            return False

    except FileNotFoundError:
        print(f"File {file_path} not found!")

if __name__ == '__main__':
    module_file_path = inspect.getfile(FilterDefaults)
    
    # Check if we already appended new_procs
    if not check_appeneded_marker(module_file_path):
        with open(module_file_path, 'a') as f:
            f.write(monkey_patch_procs)

    nbdev_docs()