import streamlit as st

from app_modules.template_loader import load_template
from app_modules.company_data import (
    fetch_company_by_org,
    format_company_data,
    search_brreg_live
)
from app_modules.Sheets.Sammendrag.summery_getter import generate_company_summary
from app_modules.Sheets.Sammendrag.manual_financial_form import show_financial_entry_form  # Manual form!
from app_modules.pdf_parser import extract_fields_from_pdf
from app_modules.Sheets.excel_filler import fill_excel
from app_modules.download import download_excel_file


def run():
    st.title("📄 PDF → Excel (BRREG, Manual Entry)")
    st.caption("Fetch company information and update Excel automatically")
    st.divider()

    # ---------------------------------------------------------
    # STEP 1: SEARCH BAR + RESULT DROPDOWN
    # ---------------------------------------------------------
    st.subheader("🔍 Find company")

    query = st.text_input(
        "Search for company",
        placeholder="Type at least 2 characters to search"
    )

    selected_company_raw = None
    company_options = []
    results = []

    if query and len(query) >= 2:
        results = search_brreg_live(query)

        if not isinstance(results, list):
            results = []

        company_options = [
            f"{c.get('navn', '')} ({c.get('organisasjonsnummer', '')})"
            for c in results
        ]

    selected_label = st.selectbox(
        "Select company",
        company_options,
        index=None,
        placeholder="Select a company"
    )

    if selected_label:
        idx = company_options.index(selected_label)
        selected_company_raw = results[idx]

    # PDF upload (always outside the IF block)
    pdf_bytes = st.file_uploader("Upload PDF", type=["pdf"])

    if not selected_company_raw:
        st.info("Select a company to continue.")
        return

    # ---------------------------------------------------------
    # STEP 2: LOAD TEMPLATE
    # ---------------------------------------------------------
    if "template_bytes" not in st.session_state:
        st.session_state.template_bytes = load_template()

    template_bytes = st.session_state.template_bytes

    # ---------------------------------------------------------
    # STEP 3: FETCH BRREG COMPANY DATA
    # ---------------------------------------------------------
    org_number = selected_company_raw.get("organisasjonsnummer")

    raw_company_data = (
        fetch_company_by_org(org_number)
        if org_number
        else selected_company_raw
    )

    company_data = format_company_data(raw_company_data)

    # ---------------------------------------------------------
    # STEP 3B: MANUAL FINANCIAL DATA ENTRY
    # ---------------------------------------------------------
    st.divider()
    
    # Show the manual entry form
    financial_data = show_financial_entry_form()
    
    # Merge financial data with company data
    company_data.update(financial_data)

    st.divider()

    # ---------------------------------------------------------
    # STEP 4: SUMMARY
    # ---------------------------------------------------------
    summary_text = generate_company_summary(company_data)

    # ---------------------------------------------------------
    # STEP 5: PDF FIELDS
    # ---------------------------------------------------------
    pdf_fields = extract_fields_from_pdf(pdf_bytes) if pdf_bytes else {}

    # ---------------------------------------------------------
    # MERGE FIELDS
    # ---------------------------------------------------------
    merged_fields = {}
    merged_fields.update(company_data)
    merged_fields.update(pdf_fields)
    merged_fields["company_summary"] = summary_text

    st.divider()
    st.subheader("📋 Extracted data")

    col_left, col_right = st.columns(2)

    with col_left:
        st.write("**Company name:**", merged_fields.get("company_name", ""))
        st.write("**Organization number:**", merged_fields.get("org_number", ""))
        st.write("**Address:**", merged_fields.get("address", ""))
        st.write("**Postal code:**", merged_fields.get("post_nr", ""))
        st.write("**City:**", merged_fields.get("city", ""))
        st.write("**Employees:**", merged_fields.get("employees", ""))
        st.write("**NACE code:**", merged_fields.get("nace_code", ""))
        st.write("**NACE description:**", merged_fields.get("nace_description", ""))

    with col_right:
        st.markdown("**Summary:**")
        st.info(summary_text or "No company description available.")
        
        # Show financial data if entered
        if financial_data:
            st.markdown("**Financial data (manually entered):**")
            if merged_fields.get("sum_driftsinnt_2024"):
                st.write("Revenue 2024:", merged_fields.get("sum_driftsinnt_2024"))
            if merged_fields.get("driftsresultat_2024"):
                st.write("Operating result 2024:", merged_fields.get("driftsresultat_2024"))

    st.divider()

    # ---------------------------------------------------------
    # STEP 6 + 7: PROCESS & DOWNLOAD
    # ---------------------------------------------------------
    if st.button("🚀 Process & Update Excel", use_container_width=True):
        with st.spinner("Processing and filling Excel..."):
            excel_bytes = fill_excel(
                template_bytes=template_bytes,
                field_values=merged_fields,
                summary_text=summary_text,
            )

        download_excel_file(
            excel_bytes=excel_bytes,
            company_name=merged_fields.get("company_name", "Company")
        )
