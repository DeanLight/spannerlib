import inspect
from nbdev.processors import FilterDefaults
from nbdev.quarto import nbdev_docs

monkey_patch_procs = """
all_procs = FilterDefaults().procs()
def new_procs(self):
    procs = [proc for proc in all_procs if proc.__name__ != 'clean_magics']
    return procs
FilterDefaults.procs = new_procs
"""

if __name__ == '__main__':
    module_file_path = inspect.getfile(FilterDefaults)

    with open(module_file_path, 'a') as f:
        f.write(monkey_patch_procs)

    nbdev_docs()