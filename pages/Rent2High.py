"""
Household Rent Affordability Calculator (HUD SAFMR, Offline)

Features:
- Adults vs dependents household builder
- Monthly income per adult (combined household income)
- Current rent + rent of the place you're considering
- ZIP + bedroom selector (0–4BR)
- Uses HUD SAFMR Excel export (offline) to get local rent benchmarks
  by ZIP and bedroom size (SAFMR 0BR/1BR/2BR/3BR/4BR and 90%/110% standards).
"""

import streamlit as st
import pandas as pd
from pathlib import Path

from fpdf import FPDF
from io import BytesIO

# -------------------------------------------------------------------
# Path to the local SAFMR Excel file (adjust if needed)
# -------------------------------------------------------------------
_FMR_PATH = Path(__file__).parent / "fmr_data.xlsx"


# -------------------------------------------------------------------
# Custom CSS for better styling
# -------------------------------------------------------------------
st.markdown(
    """
    <style>
    .main-header {
        font-size: 36px;
        font-weight: bold;
        color: #2c7be5;
        text-align: center;
        margin-bottom: 30px;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
    }
    .affordability-card {
        background-color: #e8f5e9;
        border-left: 5px solid #4caf50;
    }
    .rent-comparison {
        background-color: #fff3e0;
        border-left: 5px solid #ff9800;
    }
    .warning-card {
        background-color: #ffebee;
        border-left: 5px solid #f44336;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -------------------------------------------------------------------
# Header normalization helper for HUD Excel
# -------------------------------------------------------------------
def _norm(col: str) -> str:
    """
    Normalize a HUD Excel header:
    - lower-case
    - remove all whitespace (spaces, newlines, tabs)
    This makes 'SAFMR 2BR - 90% Payment Standard' and
    'SAFMR\\n2BR -\\n90% Payment\\nStandard' look the same.
    """
    return "".join(col.lower().split())


# -------------------------------------------------------------------
# Load & clean SAFMR data
# -------------------------------------------------------------------
@st.cache_data(show_spinner=True)
def load_fmr_data() -> pd.DataFrame:
    """
    Load the HUD SAFMR Excel file and return a cleaned DataFrame with:

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

    # Map original columns → normalized string
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
    """
    Find the SAFMR row where `zip` matches the supplied ZIP and
    return SAFMR + 90/110% payment standards for the chosen bedroom.

    bedroom: 0,1,2,3,4
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
# Affordability calculation
# -------------------------------------------------------------------
def calc_rent_30pct(total_monthly_income: float) -> float:
    """Return 30% of monthly household income."""
    return round(total_monthly_income * 0.30, 2)


# -------------------------------------------------------------------
# PDF report builder
# -------------------------------------------------------------------

def build_pdf_report(
    zip_code: str,
    bedroom_label: str,
    safmr_info: dict,
    total_income: float,
    num_adults: int,
    num_dependents: int,
    current_rent: float,
    target_rent: float,
    rent_30: float,
) -> BytesIO:
    """
    Build a one-page PDF summarizing the household and rent metrics.
    Returns a BytesIO buffer ready for st.download_button.
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title (ASCII only)
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "Household Rent Snapshot", ln=1, align="C")
    pdf.ln(4)

    # Subheading
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
        f"ZIP: {zip_code}  -  HUD Area: {safmr_info.get('area_name', 'Unknown')}",
        ln=1,
    )
    pdf.cell(
        0,
        6,
        f"Adults (earners): {num_adults}  -  Dependents: {num_dependents}",
        ln=1,
    )
    pdf.cell(
        0,
        6,
        f"Total monthly household income: ${total_income:,.0f}",
        ln=1,
    )
    pdf.cell(
        0,
        6,
        f"30 percent of household income: ${rent_30:,.0f}",
        ln=1,
    )
    pdf.ln(4)

    # HUD SAFMR section
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "HUD SAFMR Benchmark", ln=1)
    pdf.set_font("Helvetica", "", 12)

    bedroom_short = bedroom_label.split()[0]  # e.g. "2" from "2 Bedroom (2BR)"
    pdf.cell(
        0,
        6,
        f"Bedroom size: {bedroom_label}",
        ln=1,
    )
    pdf.cell(
        0,
        6,
        f"SAFMR {bedroom_short}: ${safmr_info['safmr']:,.0f}",
        ln=1,
    )
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

    pdf.cell(0, 6, f"Current rent: ${current_rent:,.0f}", ln=1)
    pdf.cell(0, 6, f"Target rent: ${target_rent:,.0f}", ln=1)

    # Comparisons
    def _fmt_diff(val: float) -> str:
        return f"{val:+,.0f}"

    cur_vs_30 = current_rent - rent_30
    tgt_vs_30 = target_rent - rent_30
    cur_vs_safmr = current_rent - safmr_info["safmr"]
    tgt_vs_safmr = target_rent - safmr_info["safmr"]

    pdf.cell(
        0,
        6,
        f"Current vs 30 percent rule: {_fmt_diff(cur_vs_30)} per month",
        ln=1,
    )
    pdf.cell(
        0,
        6,
        f"Target vs 30 percent rule: {_fmt_diff(tgt_vs_30)} per month",
        ln=1,
    )
    pdf.cell(
        0,
        6,
        f"Current vs SAFMR: {_fmt_diff(cur_vs_safmr)} per month",
        ln=1,
    )
    pdf.cell(
        0,
        6,
        f"Target vs SAFMR: {_fmt_diff(tgt_vs_safmr)} per month",
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

    # Write to in-memory buffer (fpdf returns a Latin-1 encoded string)
    pdf_bytes = pdf.output(dest="S").encode("latin-1")
    buffer = BytesIO(pdf_bytes)
    return buffer

# -------------------------------------------------------------------
# Streamlit app
# -------------------------------------------------------------------
def main():
    st.markdown(
        '<h1 class="main-header">🏠 Household Rent Affordability (HUD SAFMR)</h1>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Build your household, enter your current and target rents, and compare them "
        "to 30% of your combined income and the HUD Small Area Fair Market Rents (SAFMRs) "
        "for your ZIP and bedroom size."
    )

    # 1️⃣ Load data
    fmr_df = load_fmr_data()
    if fmr_df is None or fmr_df.empty:
        st.stop()

    # 2️⃣ Sidebar inputs: household & rents
    st.sidebar.header("👨‍👩‍👧 Household")

    num_adults = st.sidebar.number_input(
        "Number of adults (income earners)",
        min_value=1,
        max_value=8,
        value=1,
        step=1,
    )

    adult_incomes = []
    for i in range(num_adults):
        income = st.sidebar.number_input(
            f"Adult {i+1} monthly gross income ($)",
            min_value=0,
            value=4000 if i == 0 else 0,
            step=100,
            key=f"adult_income_{i}",
        )
        adult_incomes.append(income)

    num_dependents = st.sidebar.number_input(
        "Number of dependents (kids / non‑earners)",
        min_value=0,
        max_value=12,
        value=0,
        step=1,
    )

    st.sidebar.header("📍 Location & Unit")

    zip_input = st.sidebar.text_input("ZIP code", value="85281")

    BEDROOM_OPTIONS = [
        ("Studio (0BR)", 0),
        ("1 Bedroom (1BR)", 1),
        ("2 Bedroom (2BR)", 2),
        ("3 Bedroom (3BR)", 3),
        ("4 Bedroom (4BR)", 4),
    ]
    bedroom_label = st.sidebar.selectbox(
        "Bedroom size (SAFMR)",
        [label for label, _ in BEDROOM_OPTIONS],
        index=2,  # default 2BR
    )
    bedroom_value = dict(BEDROOM_OPTIONS)[bedroom_label]

    st.sidebar.header("💸 Rents")

    current_rent = st.sidebar.number_input(
        "Your current monthly rent ($)",
        min_value=0,
        value=1500,
        step=50,
    )
    target_rent = st.sidebar.number_input(
        "Rent for the place you're considering ($)",
        min_value=0,
        value=1800,
        step=50,
    )

    show_debug = st.sidebar.checkbox("Show raw SAFMR row", value=False)

    # 3️⃣ Calculations
    total_income = sum(adult_incomes)
    rent_30 = calc_rent_30pct(total_income)

    safmr_info = lookup_fmr(zip_input, bedroom_value, fmr_df)
    if not safmr_info:
        st.warning(
            f"⚠️ Could not find a SAFMR entry for ZIP {zip_input} and {bedroom_label} "
            "in the local dataset. Check your Excel file or try another ZIP."
        )
        if show_debug:
            st.write("Sample ZIPs available:", fmr_df["zip"].head(10).tolist())
        st.stop()

    # 4️⃣ Top metrics: household + HUD benchmark
    household_size = num_adults + num_dependents

    st.subheader("📊 Household & Local Benchmark")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown('<div class="metric-card affordability-card">', unsafe_allow_html=True)
        st.metric("Total Monthly Household Income", f"${total_income:,.0f}")
        st.write(f"{num_adults} adults, {num_dependents} dependents")
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="metric-card affordability-card">', unsafe_allow_html=True)
        st.metric("30% of Household Income", f"${rent_30:,.0f}")
        st.write("Common affordability guideline")
        st.markdown("</div>", unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="metric-card rent-comparison">', unsafe_allow_html=True)
        st.metric(
            f"HUD SAFMR {bedroom_label.split()[0]}",
            f"${safmr_info['safmr']:,.0f}",
        )
        st.write(f"{safmr_info['area_name']}")
        st.markdown("</div>", unsafe_allow_html=True)

    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Household Size", f"{household_size} people")
        st.write("Adults + dependents")
        st.markdown("</div>", unsafe_allow_html=True)

    # 5️⃣ Rent comparison (current vs target)
    st.markdown("---")
    st.subheader("🏠 Current vs Target Rent")

    col1, col2, col3, col4 = st.columns(4)

    # Helper diffs
    def fmt_diff(val, benchmark):
        diff = val - benchmark
        sign = "+" if diff > 0 else ""
        return diff, f"{sign}${diff:,.0f}"

    cur_vs_30_diff, cur_vs_30_txt = fmt_diff(current_rent, rent_30)
    tgt_vs_30_diff, tgt_vs_30_txt = fmt_diff(target_rent, rent_30)

    cur_vs_safmr_diff, cur_vs_safmr_txt = fmt_diff(current_rent, safmr_info["safmr"])
    tgt_vs_safmr_diff, tgt_vs_safmr_txt = fmt_diff(target_rent, safmr_info["safmr"])

    with col1:
        st.markdown('<div class="metric-card rent-comparison">', unsafe_allow_html=True)
        st.metric("Current Rent", f"${current_rent:,.0f}")
        st.write(f"vs 30% rule: {cur_vs_30_txt}")
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="metric-card rent-comparison">', unsafe_allow_html=True)
        st.metric("Target Rent", f"${target_rent:,.0f}")
        st.write(f"vs 30% rule: {tgt_vs_30_txt}")
        st.markdown("</div>", unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Current vs SAFMR", cur_vs_safmr_txt)
        st.write("Positive = above HUD benchmark")
        st.markdown("</div>", unsafe_allow_html=True)

    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Target vs SAFMR", tgt_vs_safmr_txt)
        st.write("Positive = above HUD benchmark")
        st.markdown("</div>", unsafe_allow_html=True)

    # 6️⃣ Narrative analysis
    st.markdown("---")
    st.subheader("🔍 Affordability Analysis")

    # Current rent vs 30%
    if current_rent > rent_30:
        st.warning(
            f"Your **current rent** (${current_rent:,.0f}) is above 30% of your "
            f"household income (${rent_30:,.0f}). That’s a higher housing cost "
            "burden than the common guideline; make sure it still feels sustainable "
            "given your other expenses and goals."
        )
    else:
        st.success(
            f"Your **current rent** (${current_rent:,.0f}) is within 30% of your "
            f"household income (${rent_30:,.0f}). That generally leaves more room "
            "for savings, debt payoff, or other priorities."
        )

    # Target rent vs 30%
    if target_rent > rent_30:
        st.warning(
            f"The **target rent** (${target_rent:,.0f}) is above 30% of your "
            "household income. If you move, housing would take a larger slice of "
            "your budget than the typical affordability rule of thumb."
        )
    else:
        st.success(
            f"The **target rent** (${target_rent:,.0f}) is within 30% of your "
            "household income. From a pure income rule perspective, it fits the "
            "common affordability guideline."
        )

    # Rents vs SAFMR
    st.markdown(
        f"- HUD **SAFMR {bedroom_label.split()[0]}** for this ZIP: "
        f"`${safmr_info['safmr']:,.0f}`.\n"
        f"- Your **current rent** is {cur_vs_safmr_txt} relative to that benchmark.\n"
        f"- Your **target rent** is {tgt_vs_safmr_txt} relative to that benchmark."
    )

    if show_debug:
        st.markdown("#### Debug: raw SAFMR row for this ZIP")
        st.write(fmr_df[fmr_df["zip"] == str(zip_input)].head())
    
    # 7️⃣ PDF download
    pdf_buffer = build_pdf_report(
        zip_code=zip_input,
        bedroom_label=bedroom_label,
        safmr_info=safmr_info,
        total_income=total_income,
        num_adults=num_adults,
        num_dependents=num_dependents,
        current_rent=current_rent,
        target_rent=target_rent,
        rent_30=rent_30,
    )

    st.markdown("---")
    st.subheader("📄 Take this with you")
    st.download_button(
        label="Download cute PDF summary",
        data=pdf_buffer,
        file_name=f"rent_snapshot_{zip_input}.pdf",
        mime="application/pdf",
    )    
if __name__ == "__main__":
    main()