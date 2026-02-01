"""Home page - Portfolio landing page"""
import streamlit as st

st.set_page_config(
    page_title="Russell Adjei - Portfolio",
    page_icon="💼",
    layout="wide",
)

# Custom CSS for home page
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .subtitle {
        font-size: 1.3rem;
        color: #888;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Hero Section
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown('<div class="main-header">Russell Adjei</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Finance • Data • Full-Stack Development</div>', unsafe_allow_html=True)
    
    st.markdown("""
    Welcome to my portfolio! I build tools for financial analysis and data tracking.
    
    Check out my projects:
    - 📊 **Vanguard Tracker** - Real-time money market fund yields
    - 📈 **ETF Builder** - Portfolio optimization tools (coming soon)
    - 📝 **Blog** - Thoughts on finance and development
    """)

with col2:
    st.info("""
    **Quick Links**
    - [GitHub](https://github.com/russelladjei)
    - [LinkedIn](https://linkedin.com/in/russelladjei)
    - [Email](mailto:russell@example.com)
    """)

st.divider()

# Featured Projects
st.header("Featured Projects")

tab1, tab2, tab3 = st.tabs(["Vanguard Tracker", "ETF Builder", "Blog"])

with tab1:
    st.markdown("""
    ### 📊 Vanguard Money Market Fund Tracker
    
    **Live Dashboard** - Real-time scraping of 7-day SEC yields
    
    - Automated daily updates via GitHub Actions
    - Historical trend analysis
    - Compare multiple funds
    
    [Go to Tracker →](pages/01_📊_Vanguard_Tracker.py)
    """)

with tab2:
    st.markdown("""
    ### 📈 ETF Builder (Coming Soon)
    
    Portfolio optimization and analysis tools
    
    - Coming soon...
    """)

with tab3:
    st.markdown("""
    ### 📝 Blog
    
    Finance, development, and data insights
    
    [Read Articles →](pages/03_📝_Blog.py)
    """)

st.divider()

# Footer
st.markdown("""
---
**Built with:**
- Streamlit (Frontend)
- Python (Backend)
- GitHub Actions (Automation)
- Playwright (Web Scraping)

© 2026 Russell Adjei. All rights reserved.
""")
