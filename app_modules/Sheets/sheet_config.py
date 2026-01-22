# app_modules/Sheets/sheet_config.py
"""
Centralized configuration for all Excel sheets.
This file imports and aggregates all sheet mappings.
"""

# Import all sheet mappings
from app_modules.Sheets.Sammendrag.mapping import (
    CELL_MAP as SAMMENDRAG_MAP,
    transform_data as transform_sammendrag
)

from app_modules.Sheets.Alminnelig_ansvar.mapping import (
    CELL_MAP as ALMINNELIG_ANSVAR_MAP,
    transform_data as transform_alminnelig_ansvar
)

from app_modules.Sheets.Fordon.mapping import (
    CELL_MAP as FORDON_MAP,
    transform_data as transform_fordon
)

from app_modules.Sheets.Prosjekt_entreprenør.mapping import (
    CELL_MAP as PROSJEKT_MAP,
    transform_data as transform_prosjekt
)

from app_modules.Sheets.Yrkesskade.mapping import (
    CELL_MAP as YRKESSKADE_MAP,
    transform_data as transform_yrkesskade
)


# Master mapping: Excel sheet name -> field mappings
# This maps the actual Excel sheet names to their cell mappings
SHEET_MAPPINGS = {
    "Sammendrag": SAMMENDRAG_MAP,
    "Alminnelig ansvar": ALMINNELIG_ANSVAR_MAP,
    "Fordon": FORDON_MAP,
    "Prosjekt,entreprenør": PROSJEKT_MAP,
    "Yrkesskade": YRKESSKADE_MAP,
}


# Master transform functions: sheet name -> transform function
SHEET_TRANSFORMS = {
    "Sammendrag": transform_sammendrag,
    "Alminnelig ansvar": transform_alminnelig_ansvar,
    "Fordon": transform_fordon,
    "Prosjekt,entreprenør": transform_prosjekt,
    "Yrkesskade": transform_yrkesskade,
}


def get_sheet_mapping(sheet_name: str) -> dict:
    """
    Get the cell mapping for a specific sheet.
    
    Args:
        sheet_name: Name of the Excel sheet
        
    Returns:
        Dictionary mapping field names to cell references
    """
    return SHEET_MAPPINGS.get(sheet_name, {})


def get_transform_function(sheet_name: str):
    """
    Get the transform function for a specific sheet.
    
    Args:
        sheet_name: Name of the Excel sheet
        
    Returns:
        Transform function or None if not found
    """
    return SHEET_TRANSFORMS.get(sheet_name)


def transform_for_sheet(sheet_name: str, data: dict) -> dict:
    """
    Transform data for a specific sheet using its transform function.
    
    Args:
        sheet_name: Name of the Excel sheet
        data: Raw data dictionary
        
    Returns:
        Transformed data dictionary
    """
    transform_func = get_transform_function(sheet_name)
    if transform_func:
        return transform_func(data)
    return data
