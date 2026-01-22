# app_modules/Sheets/Yrkesskade/mapping.py
"""
Mapping configuration for the Yrkesskade (Occupational Injury) sheet.
This defines which data fields map to which Excel cells.
"""

# Cell mapping: field_name -> Excel cell reference
# TODO: Add your specific cell mappings for this sheet
CELL_MAP = {
    "company_name": "B2",
    "org_number": "B3",
    "employees": "B10",
    "injury_history": "B15",
    # Add more mappings as needed for this sheet
}


def transform_data(extracted: dict) -> dict:
    """
    Transform raw extracted data into the format expected by the Yrkesskade sheet.
    
    Args:
        extracted: Raw data dictionary from various sources
        
    Returns:
        Transformed dictionary with standardized field names
    """
    out = {}
    
    # Basic company info
    out["company_name"] = extracted.get("company_name") or extracted.get("name") or ""
    out["org_number"] = extracted.get("org_number") or extracted.get("org_no") or ""
    out["employees"] = extracted.get("employees") or extracted.get("antallAnsatte") or ""
    
    # Occupational injury specific fields
    out["injury_history"] = extracted.get("injury_history") or ""
    
    # Add specific transformations for this sheet
    
    return out
