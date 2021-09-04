from IPython.core.magic import (Magics, magics_class, line_cell_magic)


@magics_class
class RgxlogMagic(Magics):
    @line_cell_magic
    def rgxlog(self, line, cell=None):
        # import locally to prevent circular import issues
        from rgxlog import magic_session

        if cell:
            magic_session.run_statements(cell, print_results=True)
        else:
            magic_session.run_statements(line, print_results=True)
