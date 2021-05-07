from IPython.core.magic import register_line_cell_magic


@register_line_cell_magic
def spanner(line, cell=None):
    from rgxlog import magic_session
    # import locally to prevent circular import issues
    print("cell is", cell)
    print("line is", line)
    if cell:
        result = magic_session.run_query(cell, print_results=True)
    else:
        result = magic_session.run_query(line, print_results=True)
