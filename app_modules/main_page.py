import streamlit as st

from app_modules.template_loader import load_template
from app_modules.company_data import (
    fetch_company_by_org,
    format_company_data,
    search_brreg_live
)
from app_modules.Sheets.Sammendrag.summery_getter import generate_company_summary
from app_modules.Sheets.Sammendrag.proff_getter_DEBUG import fetch_proff_info  # ADDED: Real Proff.no getter
from app_modules.pdf_parser import extract_fields_from_pdf
from app_modules.Sheets.excel_filler import fill_excel
from app_modules.download import download_excel_file


def run():
    st.title("📄 PDF → Excel (Brønnøysund,Proff)")
    st.caption("Hent selskapsinformasjon og oppdater Excel automatisk")
    st.divider()

    # ---------------------------------------------------------
    # STEP 1: SEARCH BAR + RESULT DROPDOWN
    # ---------------------------------------------------------
    st.subheader("🔍 Finn selskap")

    query = st.text_input(
        "Søk etter selskap",
        placeholder="Skriv minst 2 bokstaver for å søke"
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
        "Velg selskap",
        company_options,
        index=None,
        placeholder="Velg et selskap"
    )

    if selected_label:
        idx = company_options.index(selected_label)
        selected_company_raw = results[idx]

    # PDF upload (always outside the IF block)
    pdf_bytes = st.file_uploader("Last opp PDF", type=["pdf"])

    if not selected_company_raw:
        st.info("Velg et selskap for å fortsette.")
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
    # STEP 3B: FETCH PROFF.NO FINANCIAL DATA
    # ---------------------------------------------------------
    st.info("🔍 Henter finansiell data fra Proff.no...")
    proff_data = {}
    
    if org_number:
        try:
            proff_data = fetch_proff_info(org_number)
            if proff_data:
                st.success(f"✅ Hentet {len(proff_data)} felt fra Proff.no")
            else:
                st.warning("⚠️ Kunne ikke hente data fra Proff.no")
        except Exception as e:
            st.warning(f"⚠️ Feil ved henting fra Proff.no: {e}")

    # Merge Proff data with company data
    # Proff data can fill in missing fields OR add new fields (like financials)
    for key, value in proff_data.items():
        if value:  # Only add non-empty values
            company_data[key] = value

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
    merged_fields.update(company_data)  # BRREG + Proff.no data
    merged_fields.update(pdf_fields)    # PDF data (overrides if conflicts)
    merged_fields["company_summary"] = summary_text

    st.divider()
    st.subheader("📋 Ekstraherte data")

    col_left, col_right = st.columns(2)

    with col_left:
        st.write("**Selskapsnavn:**", merged_fields.get("company_name", ""))
        st.write("**Organisasjonsnummer:**", merged_fields.get("org_number", ""))
        st.write("**Adresse:**", merged_fields.get("address", ""))
        st.write("**Postnummer:**", merged_fields.get("post_nr", ""))
        st.write("**Poststed:**", merged_fields.get("city", ""))
        st.write("**Antall ansatte:**", merged_fields.get("employees", ""))
        st.write("**Hjemmeside:**", merged_fields.get("homepage", ""))
        st.write("**NACE-kode:**", merged_fields.get("nace_code", ""))
        st.write("**NACE-beskrivelse:**", merged_fields.get("nace_description", ""))

    with col_right:
        st.markdown("**Sammendrag (går i 'Om oss' / 'Skriv her' celle):**")
        st.info(summary_text or "Ingen tilgjengelig selskapsbeskrivelse.")
        
        # Show financial data if available
        if proff_data:
            st.markdown("**Finansiell data (fra Proff.no):**")
            if merged_fields.get("sum_driftsinnt_2024"):
                st.write("Driftsinntekter 2024:", merged_fields.get("sum_driftsinnt_2024"))
            if merged_fields.get("driftsresultat_2024"):
                st.write("Driftsresultat 2024:", merged_fields.get("driftsresultat_2024"))

    st.divider()

    # ---------------------------------------------------------
    # STEP 6 + 7: PROCESS & DOWNLOAD
    # ---------------------------------------------------------
    if st.button("🚀 Prosesser & Oppdater Excel", use_container_width=True):
        with st.spinner("Behandler og fyller inn Excel..."):
            excel_bytes = fill_excel(
                template_bytes=template_bytes,
                field_values=merged_fields,
                summary_text=summary_text,
            )

        download_excel_file(
            excel_bytes=excel_bytes,
            company_name=merged_fields.get("company_name", "Selskap")
        )