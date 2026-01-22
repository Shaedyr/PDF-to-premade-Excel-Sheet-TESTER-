# app_modules/Sheets/Sammendrag/mapping.py
"""
Mapping configuration for the Sammendrag (Summary) sheet.
This defines which data fields map to which Excel cells.
"""

# Cell mapping: field_name -> Excel cell reference
CELL_MAP = {
    "company_name": "B3",
    "org_number": "B4",
    "address": "B5",
    "post_nr": "B6",
    "city": "B7",
    "employees": "B8",
    "nace_code": "B9",
    "nace_description": "B10",
    "homepage": "B11",
    "sum_driftsinnt_2024": "D3",
    "sum_driftsinnt_2023": "E3",
    "sum_driftsinnt_2022": "F3",
    "driftsresultat_2024": "D4",
    "driftsresultat_2023": "E4",
    "driftsresultat_2022": "F4",
    "ord_res_f_skatt_2024": "D5",
    "ord_res_f_skatt_2023": "E5",
    "ord_res_f_skatt_2022": "F5",
    "sum_eiendeler_2024": "D6",
    "sum_eiendeler_2023": "E6",
    "sum_eiendeler_2022": "F6",
}


def transform_data(extracted: dict) -> dict:
    """
    Transform raw extracted data into the format expected by the Sammendrag sheet.
    
    Args:
        extracted: Raw data dictionary from various sources
        
    Returns:
        Transformed dictionary with standardized field names
    """
    out = {}
    
    # Basic company info
    out["company_name"] = extracted.get("company_name") or extracted.get("name") or extracted.get("kunde") or ""
    out["org_number"] = extracted.get("org_number") or extracted.get("org_no") or extracted.get("organisasjonsnummer") or ""
    out["address"] = extracted.get("address") or extracted.get("adresse") or ""
    out["post_nr"] = extracted.get("post_nr") or extracted.get("postnr") or ""
    out["city"] = extracted.get("city") or extracted.get("poststed") or ""
    
    # Financial data for multiple years
    for key in ("sum_driftsinnt", "driftsresultat", "ord_res_f_skatt", "sum_eiendeler"):
        for year in ("2024", "2023", "2022"):
            out[f"{key}_{year}"] = extracted.get(f"{key}_{year}", "")
    
    # Additional fields
    out["homepage"] = extracted.get("homepage") or extracted.get("website") or ""
    out["current_insurer"] = extracted.get("current_insurer", "")
    out["tender_deadline"] = extracted.get("tender_deadline") or extracted.get("anbudsfrist") or ""
    out["economy_summary"] = extracted.get("economy_summary", "")
    out["total_pris_pr_aar"] = extracted.get("total_pris_pr_aar") or extracted.get("total_price_year") or ""
    
    return out