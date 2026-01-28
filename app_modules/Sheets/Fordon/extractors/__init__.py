# app_modules/Sheets/Fordon/extractors/__init__.py
"""
Vehicle extractors for different insurance companies.
"""

from .if_skadeforsikring import extract_if_vehicles
from .gjensidige import extract_gjensidige_vehicles

__all__ = [
    'extract_if_vehicles',
    'extract_gjensidige_vehicles',
]
