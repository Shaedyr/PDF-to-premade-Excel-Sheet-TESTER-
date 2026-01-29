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
    import streamlit as st
    
    vehicles = []
    seen_registrations = set()
    
    # Extract registered cars
    cars = _extract_registered_cars(pdf_text, seen_registrations)
    vehicles.extend(cars)
    
    # Extract unregistered tractors/machines - WITH DEBUG
    st.write("  🔎 **DEBUG: Looking for tractors...**")
    
    # Check if text contains tractor keywords
    has_uregistrert = 'uregistrert' in pdf_text.lower()
    has_traktor = 'traktor' in pdf_text.lower()
    st.write(f"    - 'uregistrert' in PDF: {has_uregistrert}")
    st.write(f"    - 'traktor' in PDF: {has_traktor}")
    
    # Check for each brand
    found_brands = []
    for brand in MACHINE_BRANDS:
        if brand in pdf_text or brand.lower() in pdf_text.lower():
            found_brands.append(brand)
    
    if found_brands:
        st.write(f"    - Found brands: {', '.join(found_brands)}")
    else:
        st.write("    - ⚠️ No machine brands found in PDF!")
    
    # Show a sample of text containing "Uregistrert"
    if has_uregistrert:
        idx = pdf_text.lower().find('uregistrert')
        sample = pdf_text[max(0, idx-50):idx+150]
        st.write(f"    - Sample text: `{sample[:100]}...`")
    
    tractors = _extract_unregistered_tractors(pdf_text)
    st.write(f"    - **Extracted: {len(tractors)} tractors**")
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
    
    Formats:
    - "Uregistrert traktor og arb.maskin - Doosan 300 DX 2023 - Uregistrert"
    - "Doosan 300 DX" (in context with "Uregistrert")
    """
    vehicles = []
    seen_machines = set()
    
    # Look for each brand in the context of "Uregistrert"
    for brand in MACHINE_BRANDS:
        # More flexible pattern: just find brand name anywhere near "Uregistrert"
        # Pattern 1: Explicit "Uregistrert traktor" line
        pattern1 = rf'Uregistrert.*?{brand}\s+([0-9A-Z\s\-]+?)(?:\s+(20\d{{2}}))?(?:\s*-|$)'
        
        for match in re.finditer(pattern1, pdf_text, re.IGNORECASE | re.DOTALL):
            model_raw = match.group(1).strip()
            year = match.group(2) if match.group(2) else None
            
            # Clean model name aggressively
            model = model_raw
            model = re.sub(r'\s*-\s*Uregistrert.*$', '', model, flags=re.I).strip()
            model = re.sub(r'\s+(arb\.?|maskin|og|as|asa).*$', '', model, flags=re.I).strip()
            model = re.sub(r'\s*\n.*$', '', model).strip()  # Remove line breaks
            
            # If no year found in match, search nearby
            if not year:
                # Search in a window around the match
                pos = match.start()
                window = pdf_text[pos:pos+200]
                year_match = re.search(r'\b(20\d{2})\b', window)
                year = year_match.group(1) if year_match else "2024"
            
            # Skip if model is empty or too short
            if not model or len(model) < 2:
                continue
            
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
        
        # Pattern 2: Brand appears in "Forsikringsoversikt" section
        # Look for brand in context of tractor insurance
        pattern2 = rf'traktor.*?{brand}\s+([0-9A-Z\s]+?)(?:\s+(20\d{{2}}))?(?:\s*-|$)'
        
        for match in re.finditer(pattern2, pdf_text, re.IGNORECASE):
            model_raw = match.group(1).strip()
            year = match.group(2) if match.group(2) else "2024"
            
            model = model_raw
            model = re.sub(r'\s*-\s*Uregistrert.*$', '', model, flags=re.I).strip()
            model = re.sub(r'\s+(arb|maskin|og).*$', '', model, flags=re.I).strip()
            
            if not model or len(model) < 2:
                continue
            
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
