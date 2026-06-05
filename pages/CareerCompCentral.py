#CareerCompCentral
import streamlit as st
import pandas as pd
from rapidfuzz import process, fuzz
from urllib.parse import quote_plus
import plotly.express as px
from fpdf import FPDF
import re


# --------------------------------------------------------------------------------------
# Page config
# --------------------------------------------------------------------------------------
st.set_page_config(
    page_title="Job Comparison – Are You Paid Fairly?",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------------------
# Styling – dark fintech look
# --------------------------------------------------------------------------------------
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

    .main-header {
        font-size: 2.1rem;
        font-weight: 800;
        letter-spacing: .05em;
        text-transform: uppercase;
        margin-bottom: 0.25rem;
    }
    .subtitle {
        font-size: 1.0rem;
        color: #9ca3af;
        margin-bottom: 1.5rem;
    }
    .disclosure {
        font-size: 0.8rem;
        color: #6b7280;
        max-width: 72ch;
    }

    /* Sidebar tweaks */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #020617 0%, #020617 40%, #030712 100%);
        border-right: 1px solid rgba(31,41,55,0.9);
    }

    /* Dataframe */
    div[data-testid="stDataFrame"] table {
        color: #e5e7eb;
    }

    h2, h3 {
        font-weight: 600;
        letter-spacing: .04em;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------------------
st.markdown('<div class="main-header">Job Comparison</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Check your pay against BLS estimates – state-level now, Super Run map + PDF for all states.</div>',
    unsafe_allow_html=True,
)

st.divider()

# --------------------------------------------------------------------------------------
# Load BLS CSV
# --------------------------------------------------------------------------------------
@st.cache_data
def load_bls_csv(path: str = "data/bls_oews_filtered.csv") -> pd.DataFrame:
    df = pd.read_csv(path)

    required_cols = {
        "area_name",
        "state",
        "occupation_code",
        "occupation_title",
        "annual_median",
        "annual_10th_percentile",
        "annual_25th_percentile",
        "annual_75th_percentile",
        "annual_90th_percentile",
        "total_employment",
    }
    missing = required_cols.difference(df.columns)
    if missing:
        raise ValueError(
            f"CSV is missing expected columns: {missing}. "
            "Check your cleaning script or column names."
        )

    df["area_name"] = df["area_name"].astype(str).str.strip()
    df["state"] = df["state"].astype(str).str.strip()
    df["occupation_title"] = df["occupation_title"].astype(str).str.strip()

    df["geo_level"] = df["state"].where(df["state"] != "US", other="US")
    return df


try:
    bls_df = load_bls_csv()
except Exception as e:
    st.error(
        "Problem loading BLS CSV. "
        "Make sure `bls_oews_filtered.csv` exists and has the expected columns.\n\n"
        f"Error: {e}"
    )
    st.stop()

# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------

def get_state_options(df: pd.DataFrame):
    states = sorted(
        {
            s
            for s in df["state"].unique()
            if isinstance(s, str) and s != "US"
        }
    )
    return states


TITLE_STOPWORDS = {
    "senior", "sr", "jr", "junior",
    "lead", "leader",
    "manager", "management",
    "assistant", "associate",
    "chief", "executive", "officer",
    "director", "vp", "president",
    "head", "staff", "worker",
    "level", "ii", "iii", "iv",
    "intern", "trainee",
}

EXEC_WORDS = {
    "chief", "executive", "officer",
    "director", "vp", "president",
    "ceo", "cfo", "coo",
}

TOKEN_RE = re.compile(r"[a-z0-9]+")


def extract_tokens(title: str) -> set:
    """Lowercase, alphanumeric tokens, drop short junk and stopwords."""
    if not isinstance(title, str):
        return set()
    tokens = TOKEN_RE.findall(title.lower())
    return {t for t in tokens if len(t) >= 3 and t not in TITLE_STOPWORDS}


def fuzzy_match_titles(user_title: str, titles: pd.Series, limit: int = 5):
    """Smarter matcher with token overlap + fuzz ratio, avoids exec titles by default."""
    user_tokens = extract_tokens(user_title)
    if not user_tokens:
        return []

    cleaned_titles = (
        titles.dropna()
        .astype(str)
        .str.strip()
        .str.lower()
        .unique()
        .tolist()
    )

    candidates = []
    user_has_exec = bool(user_tokens & EXEC_WORDS)

    for t in cleaned_titles:
        cand_tokens = extract_tokens(t)
        overlap = len(user_tokens & cand_tokens)
        cand_has_exec = bool(cand_tokens & EXEC_WORDS)

        if cand_has_exec and not user_has_exec:
            continue

        score = fuzz.WRatio(user_title.lower().strip(), t)

        if overlap > 0 and score >= 65:
            candidates.append((t, score, overlap))
        elif score >= 85:
            candidates.append((t, score, overlap))

    if not candidates:
        return []

    candidates.sort(key=lambda x: (x[2], x[1]), reverse=True)
    top = candidates[:limit]

    return [(t, score, 0) for (t, score, overlap) in top]


def label_position(user_salary: float, median: float) -> str:
    if pd.isna(median) or user_salary <= 0:
        return "N/A"
    pct_diff = (user_salary - median) / median
    if pct_diff < -0.1:
        return "Below median (>10% under)"
    elif pct_diff < 0.1:
        return "Near median (±10%)"
    else:
        return "Above median (>10% over)"


def compute_state_summary(df_state: pd.DataFrame, job_title: str, salary: float):
    """For one state subset, fuzzy match titles and return summary metrics."""
    matches = fuzzy_match_titles(job_title, df_state["occupation_title"], limit=5)
    if not matches:
        return None

    top_titles = [m[0] for m in matches]
    df_matches = df_state[df_state["occupation_title"].str.lower().isin(top_titles)]

    if df_matches.empty:
        return None

    approx_median = float(df_matches["annual_median"].median())
    delta = salary - approx_median
    position = label_position(salary, approx_median)

    nice_titles = sorted({t.title() for t in top_titles})

    return {
        "approx_median": approx_median,
        "delta": delta,
        "position": position,
        "matched_titles": nice_titles,
    }


# --------------------------------------------------------------------------------------
# Sidebar inputs
# --------------------------------------------------------------------------------------
st.sidebar.header("Inputs")

job_title = st.sidebar.text_input("Job title", value="Financial Representative")

state_options = get_state_options(bls_df)
default_state_index = state_options.index("AZ") if "AZ" in state_options else 0
selected_state = st.sidebar.selectbox(
    "State code",
    options=state_options,
    index=default_state_index,
)

current_salary = st.sidebar.number_input(
    "Your current / offer salary (annual, USD)",
    min_value=0,
    step=1000,
    value=76000,
)

st.sidebar.markdown("---")
run_button = st.sidebar.button("Run (single state)")
super_run_button = st.sidebar.button("Super Run (all states)")

st.sidebar.markdown("---")
st.sidebar.markdown(
    "Data source: U.S. Bureau of Labor Statistics – Occupational Employment and "
    "Wage Statistics (OEWS). Figures are estimates and may not reflect your exact "
    "role or situation."
)

# --------------------------------------------------------------------------------------
# Single-state run
# --------------------------------------------------------------------------------------
if run_button:
    if not job_title.strip():
        st.warning("Please enter a job title to run the comparison.")
    else:
        df_state = bls_df[(bls_df["state"] == selected_state)]
        if df_state.empty:
            st.warning(f"No rows found for state `{selected_state}` in the CSV.")
        else:
            summary = compute_state_summary(df_state, job_title, current_salary)
            if summary is None:
                st.warning(
                    "Could not confidently match that job title to BLS occupations "
                    "in this state. Try a more generic title (e.g., 'Software Developer')."
                )
            else:
                approx_median = summary["approx_median"]
                delta = summary["delta"]
                position = summary["position"]
                matched_titles = summary["matched_titles"]

                st.subheader(f"Results – {selected_state}")
                st.caption("Matched BLS occupation titles (fuzzy match):")
                for t in matched_titles:
                    st.write(f"- {t}")

                df_display = bls_df[
                    (bls_df["state"] == selected_state)
                    & (
                        bls_df["occupation_title"].str.lower().isin(
                            [t.lower() for t in matched_titles]
                        )
                    )
                ][
                    [
                        "occupation_title",
                        "area_name",
                        "annual_10th_percentile",
                        "annual_25th_percentile",
                        "annual_median",
                        "annual_75th_percentile",
                        "annual_90th_percentile",
                        "total_employment",
                    ]
                ].copy()

                st.markdown("### BLS wage estimates vs your salary (state-level)")
                st.dataframe(
                    df_display.style.format(
                        {
                            "annual_10th_percentile": "${:,.0f}",
                            "annual_25th_percentile": "${:,.0f}",
                            "annual_median": "${:,.0f}",
                            "annual_75th_percentile": "${:,.0f}",
                            "annual_90th_percentile": "${:,.0f}",
                            "total_employment": "{:,.0f}",
                        }
                    ),
                    hide_index=True,
                )

                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("Approx. BLS median (matched rows)", f"${approx_median:,.0f}")
                with col_b:
                    st.metric("Your salary", f"${current_salary:,.0f}")
                with col_c:
                    st.metric(position, f"${delta:,.0f}")

                st.markdown("### Quick take")
                st.write(
                    "This comparison uses BLS OEWS state-level estimates for occupations whose titles "
                    "are fuzzy-matched to your input. Treat it as a **signal**, not an exact quote."
                )

                st.markdown("### Live job postings (Indeed)")
                indeed_q = quote_plus(job_title)
                indeed_loc = quote_plus(selected_state)
                indeed_url = f"https://www.indeed.com/jobs?q={indeed_q}&l={indeed_loc}"
                st.markdown(
                    f"[Open search on Indeed →]({indeed_url})  \n"
                    "Note: Job postings and listed salaries come from Indeed and may differ from BLS estimates."
                )

# --------------------------------------------------------------------------------------
# Super Run – all states + PDF + map
# --------------------------------------------------------------------------------------
summary_df = None

if super_run_button:
    if not job_title.strip():
        st.warning("Please enter a job title before Super Run.")
    else:
        st.subheader("Super Run – All States")
        rows = []
        state_codes = get_state_options(bls_df)

        for state_code in state_codes:
            df_state = bls_df[bls_df["state"] == state_code]
            if df_state.empty:
                continue

            summary = compute_state_summary(df_state, job_title, current_salary)
            if summary is None:
                continue

            rows.append(
                {
                    "state": state_code,
                    "approx_median": summary["approx_median"],
                    "delta_vs_salary": summary["delta"],
                    "position": summary["position"],
                    "matched_titles": ", ".join(summary["matched_titles"][:5]),
                }
            )

        if not rows:
            st.warning(
                "Super Run did not find good matches across states for this job title. "
                "Try a more generic title."
            )
        else:
            summary_df = pd.DataFrame(rows)
            summary_df = summary_df.sort_values("approx_median", ascending=False).reset_index(drop=True)

            st.markdown("### State rankings (by approximate BLS median)")
            st.dataframe(
                summary_df.style.format(
                    {
                        "approx_median": "${:,.0f}",
                        "delta_vs_salary": "${:,.0f}",
                    }
                ),
                hide_index=True,
            )

            # ---------------- PDF generation ----------------
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            pdf.set_font("helvetica", "B", 16)

            def clean(text: str) -> str:
                return (
                    str(text)
                    .replace("–", "-")
                    .replace("—", "-")
                    .replace("“", '"')
                    .replace("”", '"')
                    .encode("ascii", "ignore")
                    .decode("ascii")
                )

            pdf.cell(0, 10, clean(f"Job Comparison - {job_title}"), ln=1)

            pdf.set_font("helvetica", "", 12)
            pdf.cell(0, 8, clean(f"Your salary: ${current_salary:,.0f}"), ln=1)
            pdf.ln(2)

            first_titles = summary_df.loc[0, "matched_titles"]
            pdf.set_font("helvetica", "B", 12)
            pdf.cell(0, 8, "Example matched BLS titles:", ln=1)
            pdf.set_font("helvetica", "", 11)

            for t in first_titles.split(", "):
                pdf.cell(0, 6, clean(f"- {t}"), ln=1)

            pdf.ln(4)
            pdf.set_font("helvetica", "B", 12)
            pdf.cell(0, 8, "State-level summary:", ln=1)
            pdf.set_font("helvetica", "", 11)

            for _, row in summary_df.iterrows():
                pdf.ln(2)
                pdf.set_font("helvetica", "B", 11)
                pdf.cell(0, 6, clean(f"{row['state']}"), ln=1)
                pdf.set_font("helvetica", "", 11)
                pdf.cell(0, 6, clean(f"Approx. BLS median: ${row['approx_median']:,.0f}"), ln=1)
                pdf.cell(
                    0,
                    6,
                    clean(
                        f"Delta vs your salary: ${row['delta_vs_salary']:,.0f} ({row['position']})"
                    ),
                    ln=1,
                )

            pdf_bytes = bytes(pdf.output(dest="S"))

            st.download_button(
                label="Download Super Run PDF",
                data=pdf_bytes,
                file_name=f"job_comparison_{job_title.replace(' ', '_')}.pdf",
                mime="application/pdf",
            )

            # ---------------- Choropleth map ----------------
            st.markdown("### U.S. map – higher median ⇒ brighter teal")

            fig = px.choropleth(
                summary_df,
                locations="state",
                locationmode="USA-states",
                color="approx_median",
                hover_name="state",
                hover_data={
                    "approx_median": ":,.0f",
                    "delta_vs_salary": ":,.0f",
                    "position": True,
                },
                color_continuous_scale=["#f9fafb", "#bbf7d0", "#22c55e"],
                scope="usa",
                labels={"approx_median": "Approx. BLS median"},
                template="plotly_dark",
            )

            fig.update_layout(
                geo=dict(
                    showframe=False,
                    showcoastlines=False,
                    projection_type="albers usa",
                    bgcolor="rgba(15,23,42,1)",
                ),
                margin=dict(l=0, r=0, t=40, b=0),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                coloraxis_colorbar=dict(
                    title="Median",
                    tickformat="$,",
                ),
            )

            st.plotly_chart(fig, use_container_width=True)

st.divider()

# --------------------------------------------------------------------------------------
# Disclosures
# --------------------------------------------------------------------------------------
st.markdown(
    """
    <div class="disclosure">
    <strong>Disclosures:</strong> Compensation figures are based on U.S. Bureau of Labor Statistics
    Occupational Employment and Wage Statistics (OEWS) data and are provided for informational and educational
    purposes only. They are estimates and may not reflect your specific role, employer, skills, or market conditions.
    This tool does not provide individualized investment, tax, or legal advice, and nothing shown here should be
    construed as a recommendation or guarantee of future compensation.
    </div>
    """,
    unsafe_allow_html=True,
)
