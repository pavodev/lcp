"""
Do not add type annotations yet
"""

import inspect
import logging
import traceback

from decorator import decorator


@decorator
def logged(f, *args, **kwargs):
    """
    Decorator that logs start and end of a function call...

    If this gets turned to C then it fails because we can't inspect it
    """
    stargs = [str(a) for a in args]
    stkwargs = {str(k): str(v) for k, v in kwargs.items()}
    details = {
        "couplet": str(uuid4()),
        "event": "called",
        "args": stargs,
        "kwargs": stkwargs,
    }
    logging.info(f"Called: {f.__name__}", extra=details)
    try:
        result = f(*args, **kwargs)
    except Exception as err:
        exc = {"event": "error", "error": str(err), "tb": traceback.format_exc()}
        details.update(exc)
        msg = f"Errored: {f.__name__} threw {type(err).__name__} ({str(err)})"
        logging.error(msg, extra=details)
        raise err
    # if inspect.isawaitable(result)
    #    result = await result
    details.update({"event": "returned"})
    logging.info(f"Returned: {type(result).__name__} from {f.__name__}", extra=details)
    return result
