# Russell Adjei Portfolio - Multi-Tool Dashboard

Your personal portfolio website with auto-updating Vanguard tracker, ETF builder, and blog.

**Live at:** [russelladjei.com](https://russelladjei.com)

## 📋 What's Inside

- **🏠 Home Page** - Portfolio landing
- **💰 Vanguard Tracker** - Auto-updating money market fund yields
- **📈 ETF Builder** - Coming soon
- **📝 Blog** - Content section
- **⚙️ GitHub Actions** - Daily auto-scrape of Vanguard data

## 🚀 Quick Start

### 1. Clone & Setup Locally

```bash
git clone https://github.com/YOUR_USERNAME/russelladjei-portfolio.git
cd russelladjei-portfolio

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Run locally
streamlit run app.py
```

Visit: `http://localhost:8501`

### 2. Deploy to Streamlit Cloud

1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click "New app"
4. Select your repo, branch: `main`, file: `app.py`
5. Deploy!

### 3. Add Custom Domain

1. Buy `russelladjei.com` at [Namecheap](https://namecheap.com)
2. In Streamlit Cloud settings → Custom domain
3. Follow CNAME setup instructions
4. Wait ~24 hours for DNS

## 📁 Project Structure

```
russelladjei-portfolio/
├── app.py                          # Home page
├── pages/
│   ├── 01_📊_Vanguard_Tracker.py   # Tracker dashboard
│   ├── 02_📈_ETF_Builder.py         # (Add later)
│   ├── 03_📝_Blog.py                # (Add later)
│   └── 04_💼_About.py               # (Add later)
├── scripts/
│   └── scrape_vanguard.py          # Daily scraper
├── data/
│   └── vanguard_yields.json        # Committed to repo (auto-updated)
├── .github/workflows/
│   └── scrape.yml                  # GitHub Actions automation
├── .streamlit/
│   └── config.toml                 # Streamlit config
├── requirements.txt
└── README.md
```

## 🤖 GitHub Actions Automation

**Daily auto-scrape schedule:**
- ⏰ Runs: 9 AM EST, Monday-Friday
- 📊 Fetches: Vanguard money market yields
- 💾 Saves: `data/vanguard_yields.json`
- 🚀 Deploys: Streamlit Cloud auto-updates

### Setup GitHub Actions

1. Go to repo → Settings → Actions → General
2. ✅ Workflow permissions → "Read and write"
3. ✅ Allow GitHub Actions to create PRs
4. Save

The `.github/workflows/scrape.yml` handles everything else!

### Manual Trigger (Optional)

Force a scrape without waiting for schedule:

```bash
# Go to GitHub repo → Actions tab
# Click "Daily Vanguard Scrape" workflow
# Click "Run workflow" → "Run workflow"
```

## 💻 Terminal Workflow

### Make Changes Locally

```bash
# Edit your code
nano pages/01_📊_Vanguard_Tracker.py

# Test locally
streamlit run app.py

# Push to GitHub (auto-deploys)
git add .
git commit -m "Update: [description]"
git push
```

### Monitor Auto-Scrape

```bash
# Go to GitHub repo
# Actions tab → "Daily Vanguard Scrape"
# See all runs + logs
```

### Pull Latest Data

```bash
# Get newest scraped data
git pull origin main
cat data/vanguard_yields.json
```

## 📝 Adding New Pages

### Add ETF Builder (When Ready)

```bash
# You provide the code
# I save it as: pages/02_📈_ETF_Builder.py
# Update requirements.txt if needed
# Push to GitHub
# Auto-deploys! ✅
```

### Add Blog Posts

```bash
# Create markdown files
mkdir -p data/blog
echo "# My Post\nContent..." > data/blog/post-1.md

# Reference in: pages/03_📝_Blog.py
# Streamlit reads and displays
```

## 🔑 Environment Variables (If Needed)

For API keys or secrets:

1. GitHub repo → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `MY_SECRET`, Value: `your_value`
4. Access in workflows: `${{ secrets.MY_SECRET }}`

## 🐛 Debugging

### Check Scraper Logs

```bash
# GitHub repo → Actions tab
# Click latest run
# See all output + errors
```

### Manual Data Entry

If auto-scrape fails, manually add data via sidebar:
- Navigate to Vanguard Tracker page
- Use "Manual Entry" section
- Enter yield + save
- Local data persists

### Reset Data

```bash
# Via sidebar: Click "Clear All Data"
# Or via terminal:
rm data/vanguard_yields.json
git add .
git commit -m "Reset: Clear all yields"
git push
```

## 📊 Data Format

`data/vanguard_yields.json` structure:

```json
{
  "VMRXX": {
    "name": "Vanguard Cash Reserves Federal Money Market Fund",
    "history": {
      "2024-01-15": 5.23,
      "2024-01-16": 5.24,
      "2024-01-17": 5.25
    }
  },
  "VMFXX": { ... }
}
```

## 🌐 DNS Setup (Custom Domain)

After buying domain:

1. Streamlit Cloud → Settings → Custom domain
2. Enter: `russelladjei.com`
3. Copy CNAME record
4. Namecheap → DNS Settings
5. Add CNAME record
6. Wait 24 hours

## 🚨 Troubleshooting

| Issue | Solution |
|-------|----------|
| Scraper fails | Check `.github/workflows/scrape.yml` logs |
| Data not updating | Verify GitHub Actions has "Read and write" permissions |
| App won't deploy | Check `requirements.txt` for syntax errors |
| Can't access locally | Ensure `pip install -r requirements.txt` worked |
| No yields found | Check `vanguard_page_debug.html` in scraper run logs |

## 📚 Resources

- [Streamlit Docs](https://docs.streamlit.io)
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Playwright Docs](https://playwright.dev/python)
- [Namecheap DNS Help](https://www.namecheap.com/support/knowledgebase/)

## 🤝 Contributing

This is your personal portfolio, but feel free to:
- Add new pages/tools
- Improve the scraper
- Add blog posts
- Expand functionality

## 📄 License

This project is your own. Modify as needed!

---

**Questions?** Check the GitHub Actions logs or test locally first.

**Happy building!** 🚀
