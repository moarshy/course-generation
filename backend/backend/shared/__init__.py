"""
Shared models and utilities for Course Creator backend services.

This package contains common models, enums, and utilities used by both
the API server and Celery workers.
"""

from .models import *
from .enums import *
from .utils import *

__version__ = "0.1.0" 