from IPython.core.magic import (Magics, magics_class, line_cell_magic)


@magics_class
class RgxlogMagic(Magics):
    @line_cell_magic
    # TODO@niv: dean, maybe rename this to rgxlog?
    def spanner(self, line, cell=None):
        from rgxlog import magic_session
        # import locally to prevent circular import issues
        if cell:
            magic_session.run_query(cell, print_results=True)
        else:
            magic_session.run_query(line, print_results=True)
