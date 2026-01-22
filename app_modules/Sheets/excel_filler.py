from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Alignment
from io import BytesIO
from app_modules.Sheets.sheet_config import SHEET_MAPPINGS, transform_for_sheet

HEADLINE_COLORS = ["FF0BD7B5", "0BD7B5"]


def fill_excel(template_bytes, field_values, summary_text):
    """
    Fill Excel template with data from field_values.
    
    Args:
        template_bytes: Excel template file as bytes
        field_values: Dictionary of field values to fill
        summary_text: Company summary text
        
    Returns:
        Filled Excel file as bytes
    """
    wb = load_workbook(filename=BytesIO(template_bytes))

    # Process each sheet that has a mapping configured
    for sheet_name, cell_map in SHEET_MAPPINGS.items():
        if sheet_name not in wb.sheetnames:
            continue

        ws = wb[sheet_name]
        
        # Transform data for this specific sheet
        transformed_data = transform_for_sheet(sheet_name, field_values)

        # Fill cells according to the mapping
        for field_key, cell_ref in cell_map.items():
            value = transformed_data.get(field_key, "")

            cell = ws[cell_ref]

            # Skip cells with headline colors (headers)
            fill = cell.fill
            if (
                fill and isinstance(fill, PatternFill)
                and fill.fgColor and fill.fgColor.rgb
                and fill.fgColor.rgb.upper() in HEADLINE_COLORS
            ):
                continue

            cell.value = value

    # Handle summary text placement in first sheet
    first_sheet = wb.sheetnames[0]
    ws_first = wb[first_sheet]

    if summary_text:
        placed = False
        for row in ws_first.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and "skriv her" in cell.value.lower():
                    cell.value = summary_text
                    cell.alignment = Alignment(wrap_text=True, vertical="top")
                    placed = True
                    break
            if placed:
                break

        if not placed:
            ws_first["A46"] = summary_text
            ws_first["A46"].alignment = Alignment(wrap_text=True, vertical="top")

    # Save and return
    out = BytesIO()
    wb.save(out)
    out.seek(0)
    return out.getvalue()
