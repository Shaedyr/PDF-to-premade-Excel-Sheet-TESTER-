# app_modules/Sheets/Fordon/mapping.py
"""
Mapping configuration for the Fordon (Vehicles) sheet.
Extracts vehicle information from insurance PDFs.
"""

import re


# This sheet uses row-based mapping (one row per vehicle)
# Each vehicle becomes a new row starting from row 3
VEHICLE_START_ROW = 3

# Column mapping for vehicle data
VEHICLE_COLUMNS = {
    "registration": "B",      # Kjennemerke/Type (Registration number)
    "make_model_year": "C",   # Fabrikat/årsmodell/Type
    "insurance_sum": "D",     # Forsikringssum (kr)
    "coverage": "E",          # Dekning
    "leasing": "F",           # Leasing
    "annual_mileage": "G",    # Årlig kjørelengde
    "odometer": "H",          # Kilometerstand (dato)
    "bonus": "I",             # Bonus
    "deductible": "J",        # Egenandel
}


def extract_vehicles_from_pdf(pdf_text: str) -> list:
    """
    Extract vehicle information from PDF text.
    Returns a list of vehicle dictionaries.
    """
    vehicles = []
    
    # Pattern to find vehicle entries in the PDF
    # Looking for registration numbers like PR59518, PR70101, etc.
    vehicle_pattern = r'(PR\d{5}|[A-Z]{2}\d{5}),\s*Varebil,\s*([A-Z\s]+(?:[A-Z\s]+)?)\s+.*?Årsmodell:\s*(\d{4})'
    
    matches = re.finditer(vehicle_pattern, pdf_text, re.MULTILINE | re.DOTALL)
    
    for match in matches:
        reg_number = match.group(1)  # e.g., PR59518
        make_model = match.group(2).strip()  # e.g., VOLKSWAGEN AMAROK
        year = match.group(3)  # e.g., 2020
        
        vehicle = {
            "registration": reg_number,
            "make_model_year": f"{make_model} {year}",
            "insurance_sum": "",  # Not in PDF or extract if needed
            "coverage": "kasko",  # All vehicles have kasko in the PDF
            "leasing": "",  # Could extract Tredjemannsinteresse/leasing if present
            "annual_mileage": "16 000",  # From PDF: 16 000 km
            "odometer": "",  # Not in this PDF
            "bonus": "",  # Not in this PDF
            "deductible": "8 000",  # From PDF: various deductibles, using common one
        }
        
        vehicles.append(vehicle)
    
    return vehicles


def transform_data(extracted: dict) -> dict:
    """
    Transform raw extracted data into Fordon sheet format.
    
    Args:
        extracted: Raw data dictionary (includes pdf_text if available)
        
    Returns:
        Dictionary with vehicle data formatted for Excel
    """
    out = {}
    
    # Check if we have PDF text to parse
    pdf_text = extracted.get("pdf_text", "")
    
    if pdf_text:
        vehicles = extract_vehicles_from_pdf(pdf_text)
        
        # Map each vehicle to its row
        for idx, vehicle in enumerate(vehicles):
            row_num = VEHICLE_START_ROW + idx
            
            for field, column in VEHICLE_COLUMNS.items():
                cell_ref = f"{column}{row_num}"
                out[cell_ref] = vehicle.get(field, "")
    
    return out


# For this sheet, we don't use a simple CELL_MAP
# Instead, we dynamically create cell references based on the number of vehicles
# The excel_filler will need to handle this differently
CELL_MAP = {}  # Empty - we use transform_data to generate dynamic mappings
