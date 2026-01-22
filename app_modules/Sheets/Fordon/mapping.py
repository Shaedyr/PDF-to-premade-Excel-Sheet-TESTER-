# app_modules/Sheets/Fordon/mapping.py
"""
Mapping configuration for the Fordon (Vehicles) sheet.
This defines which data fields map to which Excel cells.
"""

# Cell mapping: field_name -> Excel cell reference
# TODO: Add your specific cell mappings for this sheet
CELL_MAP = {
    "company_name": "B2",
    "org_number": "B3",
    "vehicle_count": "B10",
    # Add more mappings as needed for this sheet
}


def transform_data(extracted: dict) -> dict:
    """
    Transform raw extracted data into the format expected by the Fordon sheet.
    
    Args:
        extracted: Raw data dictionary from various sources
        
    Returns:
        Transformed dictionary with standardized field names
    """
    out = {}
    
    # Basic company info
    out["company_name"] = extracted.get("company_name") or extracted.get("name") or ""
    out["org_number"] = extracted.get("org_number") or extracted.get("org_no") or ""
    
    # Vehicle-specific fields
    out["vehicle_count"] = extracted.get("vehicle_count") or extracted.get("antal_fordon") or ""
    
    # Add specific transformations for this sheet
    
    return out
