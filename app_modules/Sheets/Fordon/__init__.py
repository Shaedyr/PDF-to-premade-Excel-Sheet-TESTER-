# app_modules/Sheets/Fordon/extractors/__init__.py
"""
Vehicle extractors for different insurance companies.

To add a new company:
1. Create new file: company_name_format.py
2. Add import here
3. Add to __all__
"""

from .if_format import extract_if_vehicles
from .gjensidige_format import extract_gjensidige_vehicles

__all__ = [
    'extract_if_vehicles',
    'extract_gjensidige_vehicles',
]
