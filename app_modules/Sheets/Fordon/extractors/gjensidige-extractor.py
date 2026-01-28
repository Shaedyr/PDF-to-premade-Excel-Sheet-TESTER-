# app_modules/Sheets/Fordon/extractors/gjensidige_format.py
"""
GJENSIDIGE FORMAT EXTRACTOR

PDF Formats:
------------

1. REGISTERED CARS:
VOLKSWAGEN TRANSPORTER 2020 BU 21895
- Sparebank 1 Sør-Norge ASA

2. UNREGISTERED TRACTORS:
Uregistrert traktor og arb.maskin - Doosan 300 DX 2023 - Uregistrert
"""

import re


MACHINE_BRANDS = [
    "Doosan", "Hitachi", "Caterpillar", "Liebherr", "Sennebogen",
    "Komatsu", "Volvo", "JCB", "Bobcat", "Case", "John Deere",
    "New Holland", "Kubota"
]


def extract_gjensidige_vehicles(pdf_text: str) -> list:
    """
    Extract vehicles from Gjensidige PDF.
    
    Args:
        pdf_text: Full PDF text content
        
    Returns:
        List of vehicle dictionaries
    """
    vehicles = []
    seen_registrations = set()
    
    # Extract registered cars
    cars = _extract_registered_cars(pdf_text, seen_registrations)
    vehicles.extend(cars)
    
    # Extract unregistered tractors/machines
    tractors = _extract_unregistered_tractors(pdf_text)
    vehicles.extend(tractors)
    
    return vehicles


def _extract_registered_cars(pdf_text: str, seen: set) -> list:
    """
    Extract registered cars.
    
    Format: MAKE MODEL YEAR REG (with space in reg)
    Example: "VOLKSWAGEN TRANSPORTER 2020 BU 21895"
    """
    vehicles = []
    
    # Car brands (uppercase in PDF)
    brands = [
        "VOLKSWAGEN", "FORD", "TOYOTA", "MERCEDES-BENZ", "LAND ROVER",
        "CITROEN", "PEUGEOT", "VOLVO", "BMW", "AUDI", "NISSAN", "RENAULT"
    ]
    
    # Pattern: BRAND + text + YEAR + REG (with space)
    brands_pattern = '|'.join(brands)
    pattern = rf'({brands_pattern})\s+([A-Z0-9\s\-().]+?)\s+(20\d{{2}})\s+([A-Z]{{2}}\s+\d{{5}})'
    
    for match in re.finditer(pattern, pdf_text):
        make = match.group(1).strip()
        model = match.group(2).strip()
        year = match.group(3).strip()
        reg_with_space = match.group(4).strip()
        
        # Remove space from registration: "BU 21895" → "BU21895"
        reg = reg_with_space.replace(" ", "")
        
        # Skip duplicates
        if reg in seen:
            continue
        seen.add(reg)
        
        # Get section around this vehicle for leasing
        pos = match.start()
        section = pdf_text[max(0, pos-200):min(len(pdf_text), pos+500)]
        
        leasing = _extract_leasing(section, pdf_text, reg)
        bonus = _extract_bonus(pdf_text, reg)
        
        vehicles.append({
            "registration": reg,
            "vehicle_type": "bil",
            "make_model_year": f"{make} {model} {year}",
            "coverage": "kasko",
            "leasing": leasing,
            "annual_mileage": "",  # Not in this format
            "bonus": bonus,
            "deductible": "",  # Not in this format
        })
    
    return vehicles


def _extract_unregistered_tractors(pdf_text: str) -> list:
    """
    Extract unregistered tractors/machines.
    
    Format: "Uregistrert traktor og arb.maskin - Doosan 300 DX 2023"
    """
    vehicles = []
    seen_machines = set()
    
    for brand in MACHINE_BRANDS:
        # Pattern: Uregistrert + brand + model (+ optional year)
        pattern = rf'Uregistrert.*?{brand}\s+([0-9A-Z\s]+?)(?:\s+(20\d{{2}}))?(?:\s*-|\n|$)'
        
        for match in re.finditer(pattern, pdf_text, re.I):
            model = match.group(1).strip()
            year = match.group(2) if match.group(2) else "2024"
            
            # Clean model (remove trailing junk)
            model = re.sub(r'\s*-\s*Uregistrert.*$', '', model, flags=re.I).strip()
            model = re.sub(r'\s+(arb|maskin|og).*$', '', model, flags=re.I).strip()
            
            # Create unique identifier
            machine_id = f"{brand.lower()}_{model.lower()}_{year}"
            if machine_id in seen_machines:
                continue
            seen_machines.add(machine_id)
            
            vehicles.append({
                "registration": "Uregistrert",
                "vehicle_type": "traktor",
                "make_model_year": f"{brand} {model} {year}",
                "coverage": "kasko",
                "leasing": "",
                "annual_mileage": "",
                "bonus": "",
                "deductible": "",
            })
    
    return vehicles


def _extract_leasing(section: str, full_text: str, reg: str) -> str:
    """
    Extract leasing company.
    
    Gjensidige format: "- Sparebank 1 Sør-Norge ASA"
    """
    # First check the section around the vehicle
    if re.search(r'sparebank\s*1', section, re.I):
        return "Sparebank 1"
    if re.search(r'nordea\s*finans', section, re.I):
        return "Nordea Finans"
    if re.search(r'santander', section, re.I):
        return "Santander"
    if re.search(r'dnb\s*finans', section, re.I):
        return "DNB Finans"
    if re.search(r'brage\s*finans', section, re.I):
        return "BRAGE FINANS"
    
    # Also check in a larger window in the full text
    # Look for the registration followed by leasing info
    reg_pattern = rf'{reg}.*?(?:Sparebank 1|Nordea Finans|Santander|DNB Finans|BRAGE FINANS)'
    match = re.search(reg_pattern, full_text, re.I | re.DOTALL)
    
    if match:
        matched_text = match.group(0)
        if re.search(r'sparebank\s*1', matched_text, re.I):
            return "Sparebank 1"
        if re.search(r'nordea\s*finans', matched_text, re.I):
            return "Nordea Finans"
        if re.search(r'santander', matched_text, re.I):
            return "Santander"
        if re.search(r'dnb\s*finans', matched_text, re.I):
            return "DNB Finans"
        if re.search(r'brage\s*finans', matched_text, re.I):
            return "BRAGE FINANS"
    
    return ""


def _extract_bonus(full_text: str, reg: str) -> str:
    """
    Extract bonus percentage.
    Searches entire document for bonus info.
    """
    # Pattern: "AB12345: 60% bonus"
    bonus_match = re.search(rf'{reg}:\s*(\d+)%\s*bonus', full_text, re.I)
    if bonus_match:
        return bonus_match.group(1) + "%"
    
    return ""
