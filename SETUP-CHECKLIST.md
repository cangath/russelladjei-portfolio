# 🚀 Setup Checklist for russelladjei.com

## Phase 1: Local Setup (5 minutes)

- [ ] Create folder: `mkdir russelladjei-portfolio`
- [ ] Navigate: `cd russelladjei-portfolio`
- [ ] Initialize git: `git init`
- [ ] Create folders: `mkdir pages data scripts .github/workflows .streamlit`
- [ ] Copy all provided files into repo
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Install Playwright: `playwright install chromium`
- [ ] Test locally: `streamlit run app.py`
- [ ] Verify it loads at `http://localhost:8501`

## Phase 2: GitHub Setup (5 minutes)

- [ ] Go to [github.com/new](https://github.com/new)
- [ ] Create repo: `russelladjei-portfolio`
- [ ] Set to **Public**
- [ ] Copy repo URL
- [ ] Add remote: `git remote add origin https://github.com/YOUR_USERNAME/russelladjei-portfolio.git`
- [ ] Rename branch: `git branch -M main`
- [ ] Add files: `git add .`
- [ ] Commit: `git commit -m "Initial commit: Vanguard tracker + GitHub Actions"`
- [ ] Push: `git push -u origin main`
- [ ] Verify all files on GitHub.com ✅

## Phase 3: GitHub Actions Permissions (2 minutes)

- [ ] Go to your GitHub repo
- [ ] Settings → Actions → General
- [ ] Scroll to "Workflow permissions"
- [ ] Select ✅ "Read and write permissions"
- [ ] Select ✅ "Allow GitHub Actions to create pull requests"
- [ ] Click Save
- [ ] Done! Actions now has permission to commit

## Phase 4: Streamlit Cloud Deploy (5 minutes)

- [ ] Go to [share.streamlit.io](https://share.streamlit.io)
- [ ] Click "New app"
- [ ] Sign in with GitHub (if needed)
- [ ] Select repository: `russelladjei-portfolio`
- [ ] Select branch: `main`
- [ ] Select main file: `app.py`
- [ ] Click "Deploy"
- [ ] Wait 2-3 minutes for build
- [ ] Verify app loads at `https://russelladjei-portfolio.streamlit.app` ✅

## Phase 5: Custom Domain Setup (10 minutes)

### 5a: Buy Domain
- [ ] Go to [namecheap.com](https://namecheap.com)
- [ ] Search for `russelladjei.com`
- [ ] Add to cart and purchase (~$9/year)
- [ ] Wait for confirmation email

### 5b: Connect Domain
- [ ] Go to [share.streamlit.io](https://share.streamlit.io)
- [ ] Click on your app
- [ ] Settings → Custom domain
- [ ] Enter: `russelladjei.com`
- [ ] Copy the CNAME value Streamlit provides

### 5c: Add DNS Record
- [ ] Namecheap Dashboard → Manage
- [ ] Advanced DNS tab
- [ ] Add CNAME record:
  - **Host:** `@` or `www` (try both)
  - **Value:** Paste CNAME from Streamlit
  - **TTL:** 3600
- [ ] Save
- [ ] Wait 24 hours for DNS propagation

### 5d: Verify
- [ ] After 24 hours, visit `https://russelladjei.com`
- [ ] Should see your app! ✅

## Phase 6: Test GitHub Actions (3 minutes)

- [ ] Go to GitHub repo → Actions tab
- [ ] Click "Daily Vanguard Scrape" workflow
- [ ] Click "Run workflow" → "Run workflow"
- [ ] Watch it run (should take ~30-60 seconds)
- [ ] Check logs for "✅ SUCCESS"
- [ ] Verify `data/vanguard_yields.json` updated on GitHub
- [ ] Reload Streamlit app → should show new data ✅

## Phase 7: Terminal Workflow Test (3 minutes)

```bash
# Make a small change
echo "# Test change" >> README.md

# Commit and push
git add .
git commit -m "Test: Verify push workflow"
git push

# Watch Streamlit Cloud auto-redeploy
# (Takes ~30 seconds)

# Verify changes live at russelladjei.com
```

## 🎉 You're Done!

Your portfolio is now:
- ✅ Live at `russelladjei.com`
- ✅ Auto-updating Vanguard data daily
- ✅ One-command deployment (push to GitHub)
- ✅ Ready to expand with ETF Builder, Blog, etc.

---

## Next Steps

1. **Add ETF Builder** → Provide code, I integrate into `pages/02_📈_ETF_Builder.py`
2. **Create Blog Posts** → Add markdown files to `data/blog/`
3. **Customize About Page** → Edit `pages/04_💼_About.py`
4. **Update Home Page** → Edit `app.py` with your info

---

## Quick Commands

```bash
# Pull latest changes
git pull

# Make changes and deploy
git add .
git commit -m "Your message"
git push

# Check scraper status
# → GitHub repo → Actions tab

# Test locally
streamlit run app.py

# Install new package (if needed)
pip install package-name
pip freeze > requirements.txt
git add requirements.txt
git commit -m "Add: package-name"
git push
```

---

**Questions?** Check the README.md or reread the setup guide.

**Ready to expand?** Let me know your ETF Builder code! 🚀
