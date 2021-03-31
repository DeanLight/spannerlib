from IPython.core.magic import register_line_cell_magic


@register_line_cell_magic
def spanner(line, cell=None):
    from rgxlog import magic_client
    # import locally to prevent circular import issues

    result = magic_client.execute(cell)
    print(result)
