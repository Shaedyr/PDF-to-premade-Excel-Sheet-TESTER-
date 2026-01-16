import requests
from bs4 import BeautifulSoup


PROFF_BASE_URL = "https://www.proff.no/selskap/{orgnr}"


# ---------------------------------------------------------
# Fetch HTML from Proff.no
# ---------------------------------------------------------
def fetch_proff_html(org_number: str):
    """
    Downloads the Proff.no company page for the given org number.
    Returns HTML text or None.
    """

    if not org_number or not org_number.isdigit():
        return None

    url = PROFF_BASE_URL.format(orgnr=org_number)

    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.text
    except Exception:
        return None


# ---------------------------------------------------------
# Extract revenue (Sum driftsinntekter) for 2024
# ---------------------------------------------------------
def extract_revenue_2024(soup: BeautifulSoup):
    """
    Finds 'Sum driftsinntekter' for year 2024 in the Regnskap table.
    Returns integer revenue in NOK or None.
    """

    try:
        table = soup.find("table", {"class": "financial-table"})
        if not table:
            return None

        # Find header row to identify column index for 2024
        header_cells = table.find("thead").find_all("th")
        year_index = None

        for idx, th in enumerate(header_cells):
            if "2024" in th.get_text(strip=True):
                year_index = idx
                break

        if year_index is None:
            return None

        # Find the row for "Sum driftsinntekter"
        rows = table.find("tbody").find_all("tr")
        for row in rows:
            label = row.find("td").get_text(strip=True).lower()
            if "sum driftsinntekter" in label:
                cells = row.find_all("td")
                raw_value = cells[year_index].get_text(strip=True)

                # Clean number
                raw_value = raw_value.replace(" ", "").replace(".", "").replace(",", "")
                if raw_value.isdigit():
                    # Proff uses "Beløp i 1000"
                    return int(raw_value) * 1000

        return None

    except Exception:
        return None


# ---------------------------------------------------------
# Extract additional financials (optional)
# ---------------------------------------------------------
def extract_financials(soup: BeautifulSoup):
    """
    Extracts driftsresultat, resultat før skatt, sum eiendeler, egenkapital.
    Returns a dict or empty dict.
    """

    out = {}

    try:
        table = soup.find("table", {"class": "financial-table"})
        if not table:
            return out

        header_cells = table.find("thead").find_all("th")
        year_index = None

        for idx, th in enumerate(header_cells):
            if "2024" in th.get_text(strip=True):
                year_index = idx
                break

        if year_index is None:
            return out

        rows = table.find("tbody").find_all("tr")

        for row in rows:
            label = row.find("td").get_text(strip=True).lower()
            cells = row.find_all("td")

            raw_value = cells[year_index].get_text(strip=True)
            cleaned = raw_value.replace(" ", "").replace(".", "").replace(",", "")

            if cleaned.isdigit():
                value = int(cleaned) * 1000
            else:
                value = None

            if "driftsresultat" in label:
                out["driftsresultat"] = value
            elif "resultat før skatt" in label or "ord. res. f. skatt" in label:
                out["resultat_for_skatt"] = value
            elif "sum eiend" in label:
                out["sum_eiendeler"] = value
           
