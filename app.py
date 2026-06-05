import os
import streamlit as st

def get_fmp_key():
    env_key = os.environ.get("FMP_API_KEY")
    if env_key:
        return env_key
    try:
        return st.secrets["FMP_API_KEY"]
    except Exception:
        return None    

        
st.markdown("""
<style>
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(37, 99, 235, 0.10), transparent 28%),
            radial-gradient(circle at top right, rgba(16, 185, 129, 0.08), transparent 24%),
            linear-gradient(180deg, #0b1120 0%, #0f172a 45%, #111827 100%);
        color: #e5e7eb;
    }
    .block-container {
        max-width: 1180px;
        padding-top: 2.5rem;
        padding-bottom: 3rem;
    }
    .hero-wrap {
        padding: 2rem 0 1rem 0;
    }
    .eyebrow {
        display: inline-block;
        padding: 0.4rem 0.8rem;
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.04);
        color: #93c5fd;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 1rem;
    }
    .main-header {
        font-size: clamp(2.8rem, 5vw, 5.2rem);
        line-height: 0.95;
        font-weight: 800;
        letter-spacing: -0.04em;
        color: #f8fafc;
        margin-bottom: 0.8rem;
    }
    .subtitle {
        font-size: clamp(1.1rem, 1.6vw, 1.45rem);
        line-height: 1.5;
        color: #cbd5e1;
        max-width: 760px;
        margin-bottom: 1.25rem;
    }
    .hero-copy {
        font-size: 1rem;
        line-height: 1.8;
        color: #94a3b8;
        max-width: 760px;
        margin-bottom: 1.4rem;
    }
    .hero-stats {
        display: flex;
        gap: 0.9rem;
        flex-wrap: wrap;
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
    .stat-pill {
        padding: 0.8rem 1rem;
        border-radius: 16px;
        background: rgba(255, 255, 255, 0.045);
        border: 1px solid rgba(148, 163, 184, 0.14);
        color: #e2e8f0;
        min-width: 150px;
    }
    .stat-label {
        display: block;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #94a3b8;
        margin-bottom: 0.2rem;
    }
    .stat-value {
        font-size: 1rem;
        font-weight: 700;
        color: #f8fafc;
    }
    .side-card, .project-card, .footer-card {
        background: rgba(255, 255, 255, 0.045);
        border: 1px solid rgba(148, 163, 184, 0.14);
        border-radius: 22px;
        padding: 1.25rem;
        backdrop-filter: blur(10px);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.18);
    }
    .side-title {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #93c5fd;
        margin-bottom: 0.8rem;
        font-weight: 700;
    }
    .side-card a {
        color: #e5e7eb;
        text-decoration: none;
    }
    .side-card a:hover {
        color: #93c5fd;
    }
    .section-title {
        font-size: 1.7rem;
        font-weight: 750;
        color: #f8fafc;
        margin-bottom: 0.35rem;
    }
    .section-copy {
        color: #94a3b8;
        margin-bottom: 1.25rem;
    }
    .project-card {
        min-height: 250px;
        padding: 1.4rem;
    }
    .project-kicker {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #86efac;
        margin-bottom: 0.75rem;
        font-weight: 700;
    }
    .project-title {
        font-size: 1.3rem;
        font-weight: 750;
        color: #f8fafc;
        margin-bottom: 0.7rem;
    }
    .project-copy {
        color: #cbd5e1;
        line-height: 1.7;
        margin-bottom: 1rem;
    }
    .project-link {
        color: #93c5fd;
        font-weight: 700;
        margin-top: auto;
    }
    .footer-card {
        margin-top: 1rem;
        color: #94a3b8;
        line-height: 1.8;
    }
    .footer-card strong {
        color: #f8fafc;
    }
    div[data-testid="stHorizontalBlock"] {
        align-items: stretch;
    }
</style>
""", unsafe_allow_html=True)

col1, col2 = st.columns([2.2, 1])

with col1:
    st.markdown('<div class="hero-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">Russell Adjei • Finance & Economics </div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="main-header">Building financial tools that make complex decisions easier.</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="subtitle">I create practical tools focused on investing and personal finance.</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="hero-copy">This website is to showcase tools I’ve   built to help the public understand financial topics. The data pulled is publicly from available sources which will be cited. No classes or promises will be sold here!</div>',
        unsafe_allow_html=True
    )

    st.markdown("""
    <div class="hero-stats">
        <div class="stat-pill">
            <span class="stat-label">Background</span>
            <span class="stat-value">Finance + client education</span>
        </div>
        <div class="stat-pill">
            <span class="stat-label">Focus</span>
            <span class="stat-value">Practical financial tools</span>
        </div>
        <div class="stat-pill">
            <span class="stat-label">Build style</span>
            <span class="stat-value">Clear, useful, modern</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="side-card">
        <div class="side-title">Connect</div>
        <p><a href="https://linkedin.com/in/russelladjei" target="_blank">LinkedIn</a></p>
        <p><a href="mailto:Russelladjei@gmail.com">Russelladjei@gmail.com</a></p>
        <br>
        <div class="side-title">About</div>
        <p>Focused on investor education, financial clarity, and product ideas that solve real-world problems.</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

st.markdown('<div class="section-title">Live Projects</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-copy">These are the tools currently live on the site.</div>',
    unsafe_allow_html=True
)

p1, p2 = st.columns(2)
p3, p4 = st.columns(2)

with p1:
    st.markdown("""
    <div class="project-card">
        <div class="project-kicker">Markets</div>
        <div class="project-title">Money Market Tracker</div>
        <div class="project-copy">
            Track money market fund yields in a cleaner format built for quick comparisons and regular monitoring.
        </div>
        <div class="project-link">Live now</div>
    </div>
    """, unsafe_allow_html=True)

with p2:
    st.markdown("""
    <div class="project-card">
        <div class="project-kicker">Careers</div>
        <div class="project-title">CareerCompCentral</div>
        <div class="project-copy">
            A compensation-focused tool designed to make career and pay comparisons easier to understand.
        </div>
        <div class="project-link">Live now</div>
    </div>
    """, unsafe_allow_html=True)

with p3:
    st.markdown("""
    <div class="project-card">
        <div class="project-kicker">Personal Finance</div>
        <div class="project-title">Rent2High</div>
        <div class="project-copy">
            A personal finance tool built to help users think more clearly about rent, affordability, and tradeoffs.
        </div>
        <div class="project-link">Live now</div>
    </div>
    """, unsafe_allow_html=True)

with p4:
    st.markdown("""
    <div class="project-card">
        <div class="project-kicker">Portfolio Analysis</div>
        <div class="project-title">ETF Builder</div>
        <div class="project-copy">
            Build custom ETF-style baskets, compare weighting approaches, and visualize portfolio behavior more clearly.
        </div>
        <div class="project-link">Live now</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

st.markdown("""
<div class="footer-card">
    <strong>Built with</strong><br>
    Streamlit, Python, and data-focused tooling.<br><br>
    © 2026 Russell Adjei. All rights reserved.
</div>
""", unsafe_allow_html=True)