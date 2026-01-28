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
    Extract registered cars from TWO formats:
    1. "VOLKSWAGEN TRANSPORTER 2020 BU 21895"
    2. Table rows with registration numbers
    """
    vehicles = []
    
    # Car brands (uppercase in PDF)
    brands = [
        "VOLKSWAGEN", "FORD", "TOYOTA", "MERCEDES-BENZ", "LAND ROVER",
        "CITROEN", "PEUGEOT", "VOLVO", "BMW", "AUDI", "NISSAN", "RENAULT"
    ]
    
    # FORMAT 1: BRAND + text + YEAR + REG (with space)
    brands_pattern = '|'.join(brands)
    pattern1 = rf'({brands_pattern})\s+([A-Z0-9\s\-().]+?)\s+(20\d{{2}})\s+([A-Z]{{2}}\s+\d{{5}})'
    
    for match in re.finditer(pattern1, pdf_text):
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
            "annual_mileage": "",
            "bonus": bonus,
            "deductible": "",
        })
    
    # FORMAT 2: All registration numbers (table format)
    # Pattern: Any registration number
    all_regs = re.findall(r'\b([A-Z]{2}\s?\d{5})\b', pdf_text)
    
    for reg_raw in all_regs:
        reg = reg_raw.replace(" ", "")
        
        # Skip if already found
        if reg in seen:
            continue
        
        # Find this registration in context
        reg_pattern = reg_raw.replace(" ", r"\s?")
        match = re.search(rf'{reg_pattern}', pdf_text)
        if not match:
            continue
        
        pos = match.start()
        # Get larger window (1000 chars) to find make/model/year
        window = pdf_text[max(0, pos-500):min(len(pdf_text), pos+500)]
        
        # Try to find brand in window
        found_brand = None
        found_model = None
        found_year = None
        
        for brand in brands:
            if brand in window:
                found_brand = brand
                # Try to extract model after brand
                brand_match = re.search(rf'{brand}\s+([A-Z][A-Za-z0-9\s\-().]+?)(?:\s+20\d{{2}}|\s*\n|$)', window)
                if brand_match:
                    found_model = brand_match.group(1).strip()
                    # Clean model name
                    found_model = re.sub(r'\s+(Reg\.år|TFA|Årspremie).*$', '', found_model).strip()
                break
        
        # Try to find year
        year_match = re.search(r'\b(20\d{2})\b', window)
        if year_match:
            found_year = year_match.group(1)
        
        # If we found at least brand and year, add it
        if found_brand and found_year:
            if not found_model:
                found_model = ""
            
            seen.add(reg)
            
            leasing = _extract_leasing(window, pdf_text, reg)
            bonus = _extract_bonus(pdf_text, reg)
            
            make_model = f"{found_brand} {found_model}".strip()
            
            vehicles.append({
                "registration": reg,
                "vehicle_type": "bil",
                "make_model_year": f"{make_model} {found_year}",
                "coverage": "kasko",
                "leasing": leasing,
                "annual_mileage": "",
                "bonus": bonus,
                "deductible": "",
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
