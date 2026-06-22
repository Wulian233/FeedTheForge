import traceback

from api.ftb.ftb_exception import FTBException
from global_style import console, error

SIMPLE_EXCEPTIONS = (Exception, FTBException, RuntimeError, ValueError)
IGNORED_INNER_EXCEPTIONS = (KeyboardInterrupt, TimeoutError)
EXCEPTION_MAX_LINES = 5


def handle_exception(ex):
    console.print()
    _handle(ex)
    console.print()


def _handle(ex, inner=False):
    if isinstance(ex, IGNORED_INNER_EXCEPTIONS):
        return
    if type(ex) in SIMPLE_EXCEPTIONS:
        prefix = "  " if inner else "× "
        error(prefix + str(ex))
    else:
        lines = "".join(traceback.format_exception(ex)).splitlines()
        text = "\n".join(lines[:EXCEPTION_MAX_LINES])
        if inner:
            text = "  " + text.replace("\n", "\n  ")
        error(text)
    cause = ex.__cause__ or (None if ex.__suppress_context__ else ex.__context__)
    if cause is not None:
        _handle(cause, True)
