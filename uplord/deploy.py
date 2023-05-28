"""
Not to be compiled to c, so that gunicorn can access deploy:create_app
"""
from .app import create_app  # noqa: F401
