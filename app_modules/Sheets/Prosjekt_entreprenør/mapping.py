# app_modules/Sheets/Prosjekt_entreprenor/mapping.py
"""
Mapping configuration for the Prosjekt,entreprenör (Project/Contractor) sheet.
This defines which data fields map to which Excel cells.
"""

# Cell mapping: field_name -> Excel cell reference
# TODO: Add your specific cell mappings for this sheet
CELL_MAP = {
    "company_name": "B2",
    "org_number": "B3",
    "project_name": "B10",
    "project_value": "B11",
    # Add more mappings as needed for this sheet
}


def transform_data(extracted: dict) -> dict:
    """
    Transform raw extracted data into the format expected by the Prosjekt sheet.
    
    Args:
        extracted: Raw data dictionary from various sources
        
    Returns:
        Transformed dictionary with standardized field names
    """
    out = {}
    
    # Basic company info
    out["company_name"] = extracted.get("company_name") or extracted.get("name") or ""
    out["org_number"] = extracted.get("org_number") or extracted.get("org_no") or ""
    
    # Project-specific fields
    out["project_name"] = extracted.get("project_name") or ""
    out["project_value"] = extracted.get("project_value") or ""
    
    # Add specific transformations for this sheet
    
    return out
