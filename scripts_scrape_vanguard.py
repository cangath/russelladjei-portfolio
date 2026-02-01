"""
Vanguard Money Market Fund Yields Scraper
Runs automatically via GitHub Actions daily at 9 AM EST
"""
import json
from pathlib import Path
from datetime import datetime
import time
import re
import sys
from playwright.sync_api import sync_playwright

# ============================================================================
# LOGGING
# ============================================================================
def log(message):
    """Print with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)

# ============================================================================
# DATA STORAGE
# ============================================================================
DATA_FILE = Path("data/vanguard_yields.json")

def load_yields():
    """Load existing yield data"""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_yields(data):
    """Save yield data"""
    DATA_FILE.parent.mkdir(exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)
    log(f"✅ Saved yields to {DATA_FILE}")

def add_yield(ticker: str, name: str, yield_val: float, date: str = None):
    """Add a yield entry"""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    data = load_yields()
    if ticker not in data:
        data[ticker] = {
            "name": name,
            "history": {}
        }
    data[ticker]["history"][date] = yield_val
    save_yields(data)
    log(f"✅ Added {ticker} ({name}): {yield_val}% on {date}")

# ============================================================================
# VANGUARD FUNDS
# ============================================================================
VANGUARD_FUNDS = {
    'VMRXX': 'Vanguard Cash Reserves Federal Money Market Fund',
    'VMFXX': 'Vanguard Federal Money Market Fund',
    'VUSXX': 'Vanguard Treasury Money Market Fund',
    'VMSXX': 'Vanguard Municipal Money Market Fund',
    'VCTXX': 'Vanguard California Municipal Money Market Fund',
    'VYFXX': 'Vanguard New York Municipal Money Market Fund'
}

# ============================================================================
# SCRAPING WITH PLAYWRIGHT
# ============================================================================
def scrape_vanguard():
    """Scrape Vanguard money market fund yields"""
    results = {}
    
    log("=" * 70)
    log("STARTING VANGUARD SCRAPE")
    log("=" * 70)
    
    try:
        log("Initializing Playwright...")
        with sync_playwright() as p:
            log("Launching Chromium browser (headless)...")
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            log("🔄 Navigating to Vanguard money markets page...")
            try:
                page.goto(
                    'https://investor.vanguard.com/investment-products/money-markets',
                    timeout=30000,
                    wait_until='networkidle'
                )
            except Exception as e:
                log(f"⚠️ Navigation timeout, continuing: {str(e)}")
            
            log("⏳ Waiting for page to load...")
            try:
                page.wait_for_load_state('domcontentloaded', timeout=15000)
            except Exception as e:
                log(f"⚠️ DOMContentLoaded timeout: {str(e)}")
            
            log("⏳ Additional render wait (3 seconds)...")
            time.sleep(3)
            
            # Initialize results
            for ticker, name in VANGUARD_FUNDS.items():
                results[ticker] = {
                    'name': name,
                    'yield': None
                }
            
            log("🔎 Searching for fund data...")
            
            try:
                # Find all links that contain our tickers
                ticker_links = page.query_selector_all("a")
                log(f"Found {len(ticker_links)} links on page")
                
                for link in ticker_links:
                    link_text = link.text_content().strip()
                    
                    # Check if this link contains a ticker
                    for ticker in VANGUARD_FUNDS.keys():
                        if ticker in link_text:
                            log(f"🎯 Found ticker: {ticker}")
                            
                            try:
                                # Get the parent table row
                                row_text = link.evaluate(
                                    "el => el.closest('tr') ? el.closest('tr').textContent : ''"
                                )
                                
                                # Extract percentage values
                                percentages = re.findall(r'(\d+\.\d+)%', row_text)
                                
                                if len(percentages) >= 1:
                                    yield_val = float(percentages[0])
                                    results[ticker]['yield'] = yield_val
                                    log(f"   ✅ {ticker}: {yield_val}%")
                                else:
                                    log(f"   ⚠️ No percentages found for {ticker}")
                                    
                            except Exception as e:
                                log(f"   ⚠️ Error extracting row for {ticker}: {str(e)}")
                                
            except Exception as e:
                log(f"❌ Error during extraction: {str(e)}")
            
            log("🔚 Closing browser...")
            browser.close()
    
    except Exception as e:
        log(f"❌ CRITICAL ERROR: {str(e)}")
        return results
    
    # Validation
    log("\n📋 VALIDATION RESULTS:")
    found_count = 0
    for ticker, data in results.items():
        if data['yield'] is not None:
            found_count += 1
            log(f"  ✅ {ticker}: {data['yield']}%")
        else:
            log(f"  ⚠️ {ticker}: Not found")
    
    log(f"\n📊 Found {found_count}/{len(VANGUARD_FUNDS)} yields")
    log("=" * 70)
    
    return results

# ============================================================================
# MAIN EXECUTION
# ============================================================================
if __name__ == "__main__":
    log("GitHub Actions Scraper Starting...")
    log(f"Time: {datetime.now()}")
    
    # Run scraper
    results = scrape_vanguard()
    
    # Save results
    today = datetime.now().strftime("%Y-%m-%d")
    saved_count = 0
    
    for ticker, data in results.items():
        if data['yield'] is not None:
            add_yield(ticker, data['name'], data['yield'], today)
            saved_count += 1
        else:
            log(f"⚠️ Skipping {ticker} - no yield found")
    
    log(f"\n📊 FINAL: Saved {saved_count}/{len(results)} yields")
    
    if saved_count == 0:
        log("⚠️ WARNING: No yields were captured!")
        sys.exit(1)
    else:
        log("✅ SUCCESS: Scrape completed")
        sys.exit(0)
