from IPython.core.magic import (Magics, magics_class, line_cell_magic)


@magics_class
class RgxlogMagic(Magics):
    @line_cell_magic
    # TODO@niv: @dean, maybe rename this to rgxlog?
    # @response: good call. Lets do it
    def rgxlog(self, line, cell=None):
        # import locally to prevent circular import issues
        from rgxlog import magic_session

        if cell:
            magic_session.run_query(cell, print_results=True)
        else:
            magic_session.run_query(line, print_results=True)
