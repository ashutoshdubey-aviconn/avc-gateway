"""
Module warehouse.__init__

Flow:
"""

from .celery import app as celery_app

__all__ = ("celery_app",)
