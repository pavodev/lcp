try:
    from .dqd_parser import convert as dqd_to_json  # noqa: F401
except ImportError:
    pass


__version__ = "0.0.1"
