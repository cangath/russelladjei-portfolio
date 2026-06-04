"""Rent2High – HUD SAFMR Rent Affordability + Incentives

Streamlit app that compares household rents to HUD Small Area Fair Market
Rents (SAFMR) and a 30% of income guideline. Includes support for
"weeks free" rent concessions on both your current place and a new place
to compute effective monthly rent.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from fpdf import FPDF
from io import BytesIO

# -------------------------------------------------------------------
# Page config + fintech-style dark theme
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Is Your Rent Too High? ",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .stApp {
        background: radial-gradient(circle at top left, #111827 0, #020617 50%, #000000 100%);
        color: #e5e7eb;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        padding-left: 2.5rem;
        padding-right: 2.5rem;
    }

    /* Metric cards */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, rgba(16,185,129,0.08), rgba(59,130,246,0.08));
        border-radius: 0.75rem;
        padding: 0.75rem 1rem;
        border: 1px solid rgba(55,65,81,0.8);
        box-shadow: 0 18px 40px rgba(0,0,0,0.5);
    }
    div[data-testid="metric-container"] > label {
        color: #9ca3af;
        font-size: 0.80rem;
        text-transform: uppercase;
        letter-spacing: .06em;
    }
    div[data-testid="metric-container"] > div {
        color: #f9fafb;
        font-size: 1.25rem;
        font-weight: 700;
    }

    h2, h3 {
        font-weight: 600;
        letter-spacing: .04em;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------------------------
# Path to the local SAFMR Excel file (adjust if needed)
# -------------------------------------------------------------------
_FMR_PATH = Path(__file__).parent / "fmr_data.xlsx"


# -------------------------------------------------------------------
# Header normalization helper for HUD Excel
# -------------------------------------------------------------------

def _norm(col: str) -> str:
    """Normalize a HUD Excel header to a compact lower-case key."""
    return "".join(col.lower().split())


# -------------------------------------------------------------------
# Load & clean SAFMR data
# -------------------------------------------------------------------

@st.cache_data(show_spinner=True)
def load_fmr_data() -> pd.DataFrame:
    """Load the HUD SAFMR Excel file and return a cleaned DataFrame.

    Output columns include:
      zip          -> ZIP code as string
      area_name    -> HUD FMR Area Name
      safmr_0..4   -> base SAFMR for 0–4BR
      safmr_X_90   -> 90% payment standard (optional)
      safmr_X_110  -> 110% payment standard (optional)
    """

    if not _FMR_PATH.exists():
        st.error(f"⚠️ SAFMR Excel file not found: {_FMR_PATH}")
        st.stop()

    df = pd.read_excel(_FMR_PATH, engine="openpyxl")

    norms = {col: _norm(str(col)) for col in df.columns}
    rename_map: dict[str, str] = {}

    for col, n in norms.items():
        # ZIP Code
        if n == "zipcode":
            rename_map[col] = "zip"
        # HUD Fair Market Rent Area Name
        elif "hudfairmarketrentareaname" in n:
            rename_map[col] = "area_name"
        # SAFMR nBR (base)
        elif n.startswith("safmr0br") and "90%paymentstandard" not in n and "110%paymentstandard" not in n:
            rename_map[col] = "safmr_0"
        elif n.startswith("safmr1br") and "90%paymentstandard" not in n and "110%paymentstandard" not in n:
            rename_map[col] = "safmr_1"
        elif n.startswith("safmr2br") and "90%paymentstandard" not in n and "110%paymentstandard" not in n:
            rename_map[col] = "safmr_2"
        elif n.startswith("safmr3br") and "90%paymentstandard" not in n and "110%paymentstandard" not in n:
            rename_map[col] = "safmr_3"
        elif n.startswith("safmr4br") and "90%paymentstandard" not in n and "110%paymentstandard" not in n:
            rename_map[col] = "safmr_4"
        # SAFMR nBR - 90% Payment Standard
        elif "safmr0br" in n and "90%paymentstandard" in n:
            rename_map[col] = "safmr_0_90"
        elif "safmr1br" in n and "90%paymentstandard" in n:
            rename_map[col] = "safmr_1_90"
        elif "safmr2br" in n and "90%paymentstandard" in n:
            rename_map[col] = "safmr_2_90"
        elif "safmr3br" in n and "90%paymentstandard" in n:
            rename_map[col] = "safmr_3_90"
        elif "safmr4br" in n and "90%paymentstandard" in n:
            rename_map[col] = "safmr_4_90"
        # SAFMR nBR - 110% Payment Standard
        elif "safmr0br" in n and "110%paymentstandard" in n:
            rename_map[col] = "safmr_0_110"
        elif "safmr1br" in n and "110%paymentstandard" in n:
            rename_map[col] = "safmr_1_110"
        elif "safmr2br" in n and "110%paymentstandard" in n:
            rename_map[col] = "safmr_2_110"
        elif "safmr3br" in n and "110%paymentstandard" in n:
            rename_map[col] = "safmr_3_110"
        elif "safmr4br" in n and "110%paymentstandard" in n:
            rename_map[col] = "safmr_4_110"

    df = df.rename(columns=rename_map)

    required_base = ["zip", "area_name"]
    missing_base = [c for c in required_base if c not in df.columns]
    if missing_base:
        st.error(
            "The SAFMR Excel file is missing required columns after mapping:\n\n"
            + ", ".join(missing_base)
            + "\n\nCheck load_fmr_data() mapping logic."
        )
        st.write("Columns I see:", list(df.columns))
        st.stop()

    # Normalize types
    df["zip"] = df["zip"].astype(str).str.strip()
    df["area_name"] = df["area_name"].astype(str).str.strip()

    # Clean currency formatting in numeric columns (drop $ and commas)
    numeric_candidates = [c for c in df.columns if c.startswith("safmr_")]
    for c in numeric_candidates:
        df[c] = (
            df[c]
            .astype(str)
            .str.replace("$", "", regex=False)
            .str.replace(",", "", regex=False)
        )
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Drop rows without any bedroom SAFMR at all (rare)
    safmr_cols_any = [c for c in numeric_candidates if not c.endswith(("_90", "_110"))]
    df = df.dropna(subset=safmr_cols_any, how="all")

    return df


# -------------------------------------------------------------------
# Lookup helper
# -------------------------------------------------------------------

def lookup_fmr(zip_code: str, bedroom: int, fmr_df: pd.DataFrame):
    """Find SAFMR row for a given ZIP + bedroom.

    Returns a dict with keys: zip, area_name, bedroom, safmr, safmr_90, safmr_110
    or None if not found.
    """

    zip_clean = str(zip_code).strip()
    matches = fmr_df[fmr_df["zip"] == zip_clean]
    if matches.empty:
        return None

    row = matches.iloc[0]
    base_col = f"safmr_{bedroom}"
    col_90 = f"safmr_{bedroom}_90"
    col_110 = f"safmr_{bedroom}_110"

    if base_col not in row or pd.isna(row[base_col]):
        return None

    def _get_num(col_name):
        if col_name in row and pd.notna(row[col_name]):
            return float(row[col_name])
        return None

    return {
        "zip": row["zip"],
        "area_name": row.get("area_name", "Unknown HUD Area"),
        "bedroom": bedroom,
        "safmr": _get_num(base_col),
        "safmr_90": _get_num(col_90),
        "safmr_110": _get_num(col_110),
    }


# -------------------------------------------------------------------
# Affordability + incentives calculations
# -------------------------------------------------------------------

def calc_rent_30pct(monthly_income: float) -> float:
    """Return 30% of **monthly** household income."""
    return round(monthly_income * 0.30, 2)


def calc_effective_rent(monthly_rent: float, lease_months: int, weeks_free: float):
    """Calculate effective monthly rent given a weeks-free concession.

    Returns (effective_monthly_rent, total_concession_dollars).
    """
    if lease_months <= 0 or monthly_rent <= 0 or weeks_free <= 0:
        return round(monthly_rent, 2), 0.0

    weekly_rent = monthly_rent * 12.0 / 52.0
    total_gross = monthly_rent * lease_months
    total_concession = weekly_rent * weeks_free
    total_paid = max(total_gross - total_concession, 0)
    effective = total_paid / lease_months

    return round(effective, 2), round(total_concession, 2)


# -------------------------------------------------------------------
# PDF report builder
# -------------------------------------------------------------------

def build_pdf_report(
    zip_code: str,
    bedroom_label: str,
    safmr_info: dict,
    monthly_income: float,
    num_adults: int,
    num_dependents: int,
    current_rent: float,
    current_lease_months: int,
    current_weeks_free: float,
    effective_current_rent: float,
    new_rent: float,
    new_lease_months: int,
    new_weeks_free: float,
    effective_new_rent: float,
    rent_30: float,
) -> BytesIO:
    """Build a one-page PDF summarizing household + rent metrics."""

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "Household Rent Snapshot", ln=1, align="C")
    pdf.ln(4)

    # Intro
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(80, 80, 80)
    pdf.multi_cell(
        0,
        6,
        "A quick snapshot of your household income, rents, and HUD Small Area "
        "Fair Market Rent (SAFMR) benchmark for your area.",
    )
    pdf.ln(4)

    # Household section
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, "Household", ln=1)

    pdf.set_font("Helvetica", "", 12)
    pdf.cell(
        0,
        6,
        f"ZIP: {zip_code} - HUD Area: {safmr_info.get('area_name', 'Unknown')}",
        ln=1,
    )
    pdf.cell(
        0,
        6,
        f"Adults (earners): {num_adults} - Dependents: {num_dependents}",
        ln=1,
    )
    pdf.cell(0, 6, f"Total monthly household income: ${monthly_income:,.0f}", ln=1)
    pdf.cell(0, 6, f"30 percent of monthly income: ${rent_30:,.0f}", ln=1)
    pdf.ln(4)

    # HUD SAFMR section
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "HUD SAFMR Benchmark", ln=1)

    pdf.set_font("Helvetica", "", 12)
    bedroom_short = bedroom_label.split()[0]
    pdf.cell(0, 6, f"Bedroom size: {bedroom_label}", ln=1)
    pdf.cell(0, 6, f"SAFMR {bedroom_short}: ${safmr_info['safmr']:,.0f}", ln=1)

    if safmr_info.get("safmr_90") is not None:
        pdf.cell(
            0,
            6,
            f"90 percent payment standard: ${safmr_info['safmr_90']:,.0f}",
            ln=1,
        )
    if safmr_info.get("safmr_110") is not None:
        pdf.cell(
            0,
            6,
            f"110 percent payment standard: ${safmr_info['safmr_110']:,.0f}",
            ln=1,
        )
    pdf.ln(4)

    # Rents section
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "Your Rents", ln=1)
    pdf.set_font("Helvetica", "", 12)

    # Current place
    pdf.cell(0, 6, f"Current place advertised rent: ${current_rent:,.0f}", ln=1)
    pdf.cell(
        0,
        6,
        f"Effective current rent with {current_weeks_free:g} weeks free "
        f"over {current_lease_months} months: ${effective_current_rent:,.0f}",
        ln=1,
    )

    # New place
    pdf.cell(0, 6, f"New place advertised rent: ${new_rent:,.0f}", ln=1)
    pdf.cell(
        0,
        6,
        f"Effective new rent with {new_weeks_free:g} weeks free "
        f"over {new_lease_months} months: ${effective_new_rent:,.0f}",
        ln=1,
    )

    def _fmt_diff(val: float) -> str:
        return f"{val:+,.0f}"

    cur_eff_vs_30 = effective_current_rent - rent_30
    new_eff_vs_30 = effective_new_rent - rent_30
    cur_eff_vs_safmr = effective_current_rent - safmr_info["safmr"]
    new_eff_vs_safmr = effective_new_rent - safmr_info["safmr"]

    pdf.cell(
        0,
        6,
        f"Effective current vs 30 percent rule: {_fmt_diff(cur_eff_vs_30)} per month",
        ln=1,
    )
    pdf.cell(
        0,
        6,
        f"Effective new vs 30 percent rule: {_fmt_diff(new_eff_vs_30)} per month",
        ln=1,
    )
    pdf.cell(
        0,
        6,
        f"Effective current vs SAFMR: {_fmt_diff(cur_eff_vs_safmr)} per month",
        ln=1,
    )
    pdf.cell(
        0,
        6,
        f"Effective new vs SAFMR: {_fmt_diff(new_eff_vs_safmr)} per month",
        ln=1,
    )
    pdf.ln(4)

    # Soft footer
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(
        0,
        5,
        "Note: This is a simple planning tool based on HUD Small Area Fair "
        "Market Rents (SAFMRs) and the 30 percent income guideline. It is "
        "not financial advice, and everyone's situation is different.",
    )

    # Output as bytes (fpdf2 returns bytes already)
    pdf_result = pdf.output(dest="S")
    if isinstance(pdf_result, (bytes, bytearray)):
        pdf_bytes = bytes(pdf_result)
    else:  # backwards-compat with older pyfpdf
        pdf_bytes = pdf_result.encode("latin-1")

    return BytesIO(pdf_bytes)


# -------------------------------------------------------------------
# Streamlit app
# -------------------------------------------------------------------

def main():
    st.title("🏙️ Is Your Rent Too High? Yes of Course! but by how much?")
    st.caption(
        "Compare your rent to the United States Department of Housing and Urban development (HUD) Small Area Fair Market Rents (SAFMR) and the "
        "30% of income guideline. Includes support for weeks-free concessions "
        "on both your current place and a new place."
    )
    st.divider()

    fmr_df = load_fmr_data()

    # Layout
    top_left, top_right = st.columns([2, 1])

    # ------------------------------------------------------------------
    # Household & income (monthly, per earner)
    # ------------------------------------------------------------------
    with top_left:
        st.subheader("Household & Location")
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("**Household income (monthly)**")

            num_adults = st.number_input(
                "Adults (earners)",
                min_value=1,
                max_value=8,
                value=1,
                step=1,
            )

            num_dependents = st.number_input(
                "Dependents",
                min_value=0,
                max_value=10,
                value=0,
                step=1,
            )

            earner_incomes = []
            for i in range(int(num_adults)):
                income = st.number_input(
                    f"Earner {i + 1} monthly income ($)",
                    min_value=0.0,
                    step=100.0,
                    format="%.0f",
                    key=f"earner_income_{i}",
                )
                earner_incomes.append(income)

            monthly_income = float(sum(earner_incomes))
            st.markdown(f"**Total monthly household income:** ${monthly_income:,.0f}")

        with col_b:
            zip_code = st.text_input("ZIP code", value="85004")
            bedroom_label = st.selectbox(
                "Bedroom size",
                [
                    "0 Bedroom (Studio)",
                    "1 Bedroom (1BR)",
                    "2 Bedroom (2BR)",
                    "3 Bedroom (3BR)",
                    "4 Bedroom (4BR)",
                ],
            )

    # ------------------------------------------------------------------
    # Current vs new rents (both with weeks-free incentives)
    # ------------------------------------------------------------------
    with top_right:
        st.subheader("Current vs New Place")

        st.markdown("**Current place (where you live now)**")
        current_rent = st.number_input(
            "Current advertised / base rent ($/month)",
            min_value=0.0,
            step=50.0,
            format="%.0f",
        )
        current_lease_months = st.number_input(
            "Lease term for current place (months)",
            min_value=1,
            max_value=36,
            value=12,
            step=1,
        )
        current_weeks_free = st.selectbox(
            "Weeks free on current place (if you stay)",
            options=[0, 2, 4, 6, 8, 12],
            index=0,
        )

        st.markdown("---")

        st.markdown("**New place (the one you're considering)**")
        new_rent = st.number_input(
            "New place advertised rent ($/month)",
            min_value=0.0,
            step=50.0,
            format="%.0f",
        )
        new_lease_months = st.number_input(
            "New place lease term (months)",
            min_value=1,
            max_value=36,
            value=12,
            step=1,
        )
        new_weeks_free = st.selectbox(
            "Weeks free on new place",
            options=[0, 2, 4, 6, 8, 12],
            index=0,
        )

    # ------------------------------------------------------------------
    # Derived values
    # ------------------------------------------------------------------
    rent_30 = calc_rent_30pct(monthly_income) if monthly_income > 0 else 0.0

    # Bedroom integer for lookup
    bedroom_int = int(bedroom_label.split()[0])
    safmr_info = lookup_fmr(zip_code, bedroom_int, fmr_df) if zip_code else None

    # Effective rents for both current and new
    effective_current_rent, current_concession = calc_effective_rent(
        monthly_rent=current_rent,
        lease_months=int(current_lease_months),
        weeks_free=float(current_weeks_free),
    )

    effective_new_rent, new_concession = calc_effective_rent(
        monthly_rent=new_rent,
        lease_months=int(new_lease_months),
        weeks_free=float(new_weeks_free),
    )

    # ------------------------------------------------------------------
    # Top metrics row
    # ------------------------------------------------------------------
    st.markdown("")
    m1, m2, m3, m4 = st.columns(4)

    m1.metric(
        label="30% of Household Income (per month)",
        value=f"${rent_30:,.0f}",
    )

    if safmr_info is not None and safmr_info.get("safmr") is not None:
        m2.metric(
            label="HUD SAFMR (Selected BR)",
            value=f"${safmr_info['safmr']:,.0f}",
            delta=f"ZIP {safmr_info['zip']}",
        )
    else:
        m2.metric(label="HUD SAFMR (Selected BR)", value="–")

    if current_rent > 0 and rent_30 > 0:
        cur_vs_30 = effective_current_rent - rent_30
        m3.metric(
            label="Effective Current vs 30%", 
            value=f"${effective_current_rent:,.0f}",
            delta=f"{cur_vs_30:+,.0f} /mo",
        )
    else:
        m3.metric(label="Effective Current vs 30%", value="–")

    if new_rent > 0 and rent_30 > 0:
        new_vs_30 = effective_new_rent - rent_30
        m4.metric(
            label="Effective New vs 30%",
            value=f"${effective_new_rent:,.0f}",
            delta=f"{new_vs_30:+,.0f} /mo",
        )
    else:
        m4.metric(label="Effective New vs 30%", value="–")

    st.markdown("")

    # ------------------------------------------------------------------
    # Bottom layout: explanation + SAFMR table
    # ------------------------------------------------------------------
    bottom_left, bottom_right = st.columns([2, 1])

    with bottom_left:
        st.subheader("Quick Read on Your Numbers")

        if not monthly_income or safmr_info is None or safmr_info.get("safmr") is None:
            st.info(
                "Enter income, ZIP, bedroom size, and rents to see how things line up "
                "against the 30% guideline and HUD SAFMR."
            )
        else:
            lines = []
            lines.append(
                f"- 30% of your monthly income is **${rent_30:,.0f}**."
            )

            safmr_val = safmr_info["safmr"]
            lines.append(
                f"- HUD's Small Area Fair Market Rent (SAFMR) for this ZIP and bedroom "
                f"is **${safmr_val:,.0f}**."
            )

            if current_rent > 0:
                if current_weeks_free > 0:
                    lines.append(
                        f"- Your current place is **${current_rent:,.0f}** on paper, but with "
                        f"**{current_weeks_free:g} weeks free on a {int(current_lease_months)}-month lease**, "
                        f"the effective monthly rent is about **${effective_current_rent:,.0f}**."
                    )
                cur_vs_30 = effective_current_rent - rent_30
                cur_vs_safmr = effective_current_rent - safmr_val
                lines.append(
                    f"  That is **{cur_vs_30:+,.0f} per month** vs the 30% guideline and "
                    f"**{cur_vs_safmr:+,.0f} per month** vs SAFMR."
                )

            if new_rent > 0:
                if new_weeks_free > 0:
                    lines.append(
                        f"- The new place is **${new_rent:,.0f}** advertised, and with "
                        f"**{new_weeks_free:g} weeks free on a {int(new_lease_months)}-month lease**, "
                        f"the effective monthly rent is about **${effective_new_rent:,.0f}**."
                    )
                new_vs_30 = effective_new_rent - rent_30
                new_vs_safmr = effective_new_rent - safmr_val
                lines.append(
                    f"  That is **{new_vs_30:+,.0f} per month** vs the 30% guideline and "
                    f"**{new_vs_safmr:+,.0f} per month** vs SAFMR."
                )

            st.markdown("\n".join(lines))

        st.caption(
            "This is a planning tool using HUD SAFMR data and a 30% of income rule of "
            "thumb. It does not account for your full financial situation."
        )

        # PDF download
        if safmr_info is not None and safmr_info.get("safmr") is not None and monthly_income > 0:
            if st.button("Generate one-page PDF snapshot"):
                pdf_buffer = build_pdf_report(
                    zip_code=zip_code,
                    bedroom_label=bedroom_label,
                    safmr_info=safmr_info,
                    monthly_income=monthly_income,
                    num_adults=int(num_adults),
                    num_dependents=int(num_dependents),
                    current_rent=current_rent,
                    current_lease_months=int(current_lease_months),
                    current_weeks_free=float(current_weeks_free),
                    effective_current_rent=effective_current_rent,
                    new_rent=new_rent,
                    new_lease_months=int(new_lease_months),
                    new_weeks_free=float(new_weeks_free),
                    effective_new_rent=effective_new_rent,
                    rent_30=rent_30,
                )

                st.download_button(
                    label="Download PDF",
                    data=pdf_buffer,
                    file_name="rent_snapshot.pdf",
                    mime="application/pdf",
                )

    with bottom_right:
        st.subheader("HUD SAFMR Snapshot")

        if safmr_info is None:
            st.info("Enter a valid ZIP and bedroom size to see HUD SAFMR benchmarks.")
        else:
            rows = [
                {
                    "Metric": "SAFMR (base)",
                    "Amount ($/mo)": safmr_info["safmr"],
                }
            ]
            if safmr_info.get("safmr_90") is not None:
                rows.append(
                    {
                        "Metric": "90% payment standard",
                        "Amount ($/mo)": safmr_info["safmr_90"],
                    }
                )
            if safmr_info.get("safmr_110") is not None:
                rows.append(
                    {
                        "Metric": "110% payment standard",
                        "Amount ($/mo)": safmr_info["safmr_110"],
                    }
                )

            safmr_df = pd.DataFrame(rows)
            safmr_df["Amount ($/mo)"] = safmr_df["Amount ($/mo)"].map(
                lambda x: f"${x:,.0f}" if pd.notna(x) else "–"
            )

            st.dataframe(
                safmr_df,
                use_container_width=True,
                hide_index=True,
            )


if __name__ == "__main__":
    main()
