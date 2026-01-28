# app_modules/Sheets/Fordon/mapping.py
"""
FORDON SHEET - MAIN ORCHESTRATOR

This file coordinates all vehicle extractors.
Each insurance company has its own extractor in extractors/

To add a new insurance company:
1. Create extractors/company_name_format.py
2. Import it here
3. Add it to the extraction attempts below
"""

import streamlit as st
from .extractors.if_format import extract_if_vehicles
from .extractors.gjensidige_format import extract_gjensidige_vehicles


VEHICLE_ROWS = {
    "car": {"start": 3, "end": 22, "name": "Cars"},
    "trailer": {"start": 26, "end": 34, "name": "Trailers"},
    "moped": {"start": 38, "end": 46, "name": "Mopeds"},
    "tractor": {"start": 50, "end": 60, "name": "Tractors"},
    "boat": {"start": 64, "end": 72, "name": "Boats"},
}

VEHICLE_COLUMNS = {
    "registration": "B",
    "make_model_year": "C",
    "coverage": "E",
    "leasing": "F",
    "annual_mileage": "G",
    "bonus": "I",
    "deductible": "J",
}


def extract_vehicles_from_pdf(pdf_text: str) -> dict:
    """
    Main extraction orchestrator.
    Tries all available extractors and combines results.
    """
    
    st.write("🔍 **FORDON: Multi-format extraction**")
    st.info("📝 Supports: If Skadeforsikring, Gjensidige")
    
    if not pdf_text or len(pdf_text) < 1000:
        st.error("❌ PDF text too short!")
        return {}
    
    st.write(f"📄 PDF text: {len(pdf_text)} chars")
    st.write("---")
    
    all_vehicles = []
    
    # ==========================================
    # Try each extractor
    # ==========================================
    
    # 1. If Skadeforsikring
    st.write("  🔎 **If Skadeforsikring**")
    try:
        if_vehicles = extract_if_vehicles(pdf_text)
        if if_vehicles:
            st.write(f"    ✅ {len(if_vehicles)} vehicles")
            all_vehicles.extend(if_vehicles)
        else:
            st.write("    ⊘ No matches")
    except Exception as e:
        st.write(f"    ❌ Error: {e}")
    
    # 2. Gjensidige
    st.write("  🔎 **Gjensidige**")
    try:
        gjen_vehicles = extract_gjensidige_vehicles(pdf_text)
        if gjen_vehicles:
            st.write(f"    ✅ {len(gjen_vehicles)} vehicles")
            all_vehicles.extend(gjen_vehicles)
        else:
            st.write("    ⊘ No matches")
    except Exception as e:
        st.write(f"    ❌ Error: {e}")
    
    # ==========================================
    # Add new extractors here:
    # ==========================================
    # st.write("  🔎 **Tryg**")
    # try:
    #     from .extractors.tryg_format import extract_tryg_vehicles
    #     tryg_vehicles = extract_tryg_vehicles(pdf_text)
    #     if tryg_vehicles:
    #         st.write(f"    ✅ {len(tryg_vehicles)} vehicles")
    #         all_vehicles.extend(tryg_vehicles)
    #     else:
    #         st.write("    ⊘ No matches")
    # except Exception as e:
    #     st.write(f"    ❌ Error: {e}")
    
    # ==========================================
    # Process results
    # ==========================================
    
    if not all_vehicles:
        st.error("❌ No vehicles found!")
        st.warning("💡 Need a new insurance company? Add an extractor in extractors/")
        return {}
    
    # Remove duplicates (keep first occurrence)
    unique = {}
    for v in all_vehicles:
        reg = v['registration']
        if reg not in unique:
            unique[reg] = v
    
    all_vehicles = list(unique.values())
    
    # Categorize by vehicle type
    categorized = _categorize_vehicles(all_vehicles)
    
    # Display summary
    st.write("---")
    st.write("📦 **Categorized:**")
    for cat, vehs in categorized.items():
        if vehs:
            name = VEHICLE_ROWS[cat]['name']
            st.write(f"  🚗 **{name}**: {len(vehs)}")
            
            # Show first 3
            for v in vehs[:3]:
                extras = []
                if v.get('leasing'):
                    extras.append(f"Leasing: {v['leasing']}")
                if v.get('bonus'):
                    extras.append(f"Bonus: {v['bonus']}")
                if v.get('annual_mileage'):
                    extras.append(f"{v['annual_mileage']} km")
                
                extra_str = f" | {' | '.join(extras)}" if extras else ""
                st.write(f"    - {v['registration']} - {v['make_model_year']}{extra_str}")
            
            if len(vehs) > 3:
                st.write(f"    ... +{len(vehs)-3} more")
    
    total = sum(len(v) for v in categorized.values())
    st.success(f"✅ **TOTAL: {total} vehicles extracted**")
    
    return categorized


def _categorize_vehicles(vehicles: list) -> dict:
    """Categorize vehicles by type."""
    categorized = {
        "car": [],
        "trailer": [],
        "moped": [],
        "tractor": [],
        "boat": [],
    }
    
    for v in vehicles:
        vtype = v.get("vehicle_type", "").lower()
        reg = v.get("registration", "").lower()
        
        # Determine category
        if "tilhenger" in vtype:
            cat = "trailer"
        elif "moped" in vtype:
            cat = "moped"
        elif "traktor" in vtype or "uregistrert" in reg:
            cat = "tractor"
        elif "båt" in vtype:
            cat = "boat"
        else:
            cat = "car"
        
        categorized[cat].append(v)
    
    return categorized


def transform_data(extracted: dict) -> dict:
    """
    Transform extracted vehicle data to Excel cell mappings.
    
    Args:
        extracted: Dictionary with 'pdf_text' key
        
    Returns:
        Dictionary mapping Excel cells to values
    """
    
    st.write("🔄 **FORDON: transform_data**")
    st.info("✅ Fields: Leasing, Årlig kjørelengde, Bonus, Egenandel")
    
    out = {}
    pdf_text = extracted.get("pdf_text", "")
    
    if not pdf_text:
        st.error("❌ No pdf_text in extracted data!")
        return out
    
    # Extract vehicles
    categorized = extract_vehicles_from_pdf(pdf_text)
    
    if not categorized:
        st.warning("⚠️ No vehicles extracted")
        return out
    
    # Map to Excel cells
    st.write("---")
    st.write("📋 **Mapping to Excel:**")
    
    total = 0
    
    for cat, vehicles in categorized.items():
        if not vehicles:
            continue
        
        config = VEHICLE_ROWS[cat]
        start, end, name = config["start"], config["end"], config["name"]
        
        st.write(f"  📌 **{name}**: Rows {start}-{end}")
        
        for idx, vehicle in enumerate(vehicles):
            row = start + idx
            
            # Check if we exceed available rows
            if row > end:
                st.warning(f"  ⚠️ Too many {name}! Max {end-start+1} allowed, got {len(vehicles)}")
                break
            
            # Map each field to its column
            for field, column in VEHICLE_COLUMNS.items():
                cell = f"{column}{row}"
                value = vehicle.get(field, "")
                out[cell] = value
            
            # Show what was mapped
            details = f"{vehicle['registration']} - {vehicle['make_model_year']}"
            if vehicle.get('leasing'):
                details += f" | Leasing: {vehicle['leasing']}"
            if vehicle.get('annual_mileage'):
                details += f" | {vehicle['annual_mileage']} km"
            if vehicle.get('bonus'):
                details += f" | Bonus: {vehicle['bonus']}"
            if vehicle.get('deductible'):
                details += f" | Egenandel: {vehicle['deductible']}"
            
            st.write(f"    Row {row}: {details}")
            total += 1
    
    st.success(f"✅ Mapped {total} vehicles to Excel")
    
    return out


# This is required for the sheet system
CELL_MAP = {}
