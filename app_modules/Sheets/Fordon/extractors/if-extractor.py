# app_modules/Sheets/Fordon/extractors/if_skadeforsikring.py
"""
IF SKADEFORSIKRING FORMAT EXTRACTOR

PDF Format:
-----------
AB12345, Varebil, VOLKSWAGEN
TRANSPORTER
Årsmodell: 2020
Kommune: Oslo
Kjørelengde: 16 000 km
Kasko: 12 500 kr
Egenandel - Skader på eget kjøretøy: 8 000 kr
Tredjemannsinteresse/leasing: Sparebank 1

Bonus section (separate):
AB12345: 60% bonus
"""

import re


def extract_if_vehicles(pdf_text: str) -> list:
    """
    Extract vehicles from If Skadeforsikring PDF.
    
    Args:
        pdf_text: Full PDF text content
        
    Returns:
        List of vehicle dictionaries
    """
    vehicles = []
    seen_registrations = set()
    
    # Pattern: REG, Type, MAKE
    # Example: "AB12345, Varebil, VOLKSWAGEN"
    pattern = r'([A-Z]{2}\d{5}),\s*(Varebil|Personbil|Lastebil|Moped|Traktor|Båt|Tilhenger),\s*([A-Z][A-Z\s\-]+?)(?:\n|$)'
    
    for match in re.finditer(pattern, pdf_text, re.MULTILINE):
        reg = match.group(1).strip()
        
        # Skip duplicates
        if reg in seen_registrations:
            continue
        seen_registrations.add(reg)
        
        vtype = match.group(2).strip()
        make = match.group(3).strip()
        
        # Get vehicle section (next 1500 chars for all details)
        pos = match.start()
        section = pdf_text[pos:pos+1500]
        
        # Extract model from next lines
        model = _extract_model(section)
        make_model = f"{make} {model}".strip()
        
        # Extract all fields
        year = _extract_year(section)
        leasing = _extract_leasing(section)
        mileage = _extract_mileage(section)
        deductible = _extract_deductible(section)
        bonus = _extract_bonus(pdf_text, reg)
        motor_type = _extract_motor_type(section) if 'Båt' in vtype else ""
        
        # Add motor type to boats
        if motor_type:
            make_model += f" ({motor_type})"
        
        vehicles.append({
            "registration": reg,
            "vehicle_type": vtype,
            "make_model_year": f"{make_model} {year}",
            "coverage": "kasko",
            "leasing": leasing,
            "annual_mileage": mileage,
            "bonus": bonus,
            "deductible": deductible,
        })
    
    return vehicles


def _extract_model(section: str) -> str:
    """Extract model from next lines after make."""
    lines = section.split('\n')
    
    for line in lines[1:5]:  # Check next 4 lines
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
            
        # Skip if it's another registration
        if re.match(r'[A-Z]{2}\d{5}', line):
            break
            
        # Skip if it's a field name
        if any(kw in line.lower() for kw in ['årsmodell', 'kommune', 'kjørelengde', 'kasko', 'egenandel', 'motor']):
            break
        
        # This should be the model
        if line and line[0].isupper():
            return line
    
    return ""


def _extract_year(section: str) -> str:
    """Extract year from section."""
    # Look for "Årsmodell: 2020"
    year_match = re.search(r'Årsmodell:\s*(\d{4})', section)
    if year_match:
        return year_match.group(1)
    
    # Fallback: any 4-digit year
    year_match = re.search(r'\b(20[12]\d)\b', section)
    if year_match:
        return year_match.group(1)
    
    return "2024"


def _extract_leasing(section: str) -> str:
    """Extract leasing company."""
    # Look for "Tredjemannsinteresse/leasing: Company Name"
    leasing_match = re.search(r'Tredjemannsinteresse/leasing:\s*([A-ZÆØÅa-zæøå0-9\s]+?)(?:\n|$)', section, re.I)
    if leasing_match:
        company = leasing_match.group(1).strip()
        return company if company else ""
    
    # Known leasing companies
    companies = [
        "Sparebank 1",
        "Nordea Finans",
        "Santander",
        "DNB Finans",
        "BRAGE FINANS",
        "Handelsbanken",
        "BN Bank",
    ]
    
    for company in companies:
        if company in section:
            return company
    
    return ""


def _extract_mileage(section: str) -> str:
    """Extract annual mileage."""
    # Look for "Kjørelengde: 16 000 km"
    mileage_match = re.search(r'Kjørelengde:\s*(\d+\s?\d+)\s*km', section, re.I)
    if mileage_match:
        return mileage_match.group(1)
    
    return ""


def _extract_deductible(section: str) -> str:
    """Extract deductible (egenandel)."""
    # Most specific: "Egenandel - Skader på eget kjøretøy: 8 000 kr"
    deduct_match = re.search(r'Egenandel\s*-\s*Skader på eget kjøretøy:\s*(\d+\s?\d+)\s*kr', section)
    if deduct_match:
        return deduct_match.group(1)
    
    # Generic: "Egenandel: 8 000 kr"
    deduct_match = re.search(r'Egenandel[:\s-]+(\d+\s?\d+)\s*kr', section, re.I)
    if deduct_match:
        return deduct_match.group(1)
    
    return ""


def _extract_bonus(full_text: str, reg: str) -> str:
    """
    Extract bonus percentage.
    Searches entire document for: "AB12345: 60% bonus"
    """
    bonus_match = re.search(rf'{reg}:\s*(\d+)%\s*bonus', full_text, re.I)
    if bonus_match:
        return bonus_match.group(1) + "%"
    
    return ""


def _extract_motor_type(section: str) -> str:
    """Extract boat motor type."""
    if re.search(r'innenbords\s*motor', section, re.I):
        return "innenbords motor"
    if re.search(r'utenbords\s*motor', section, re.I):
        return "utenbords motor"
    if re.search(r'påhengsmotor', section, re.I):
        return "påhengsmotor"
    
    return ""
