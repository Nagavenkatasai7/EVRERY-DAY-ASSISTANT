# 🚀 Quick Start Guide

## Start Using Your AI Research Assistant in 3 Steps!

### Step 1: Navigate to Project
```bash
cd /Users/nagavenkatasaichennu/Desktop/extension/research-assistant
```

### Step 2: Launch Application
```bash
./start.sh
```

Or manually:
```bash
streamlit run app.py
```

### Step 3: Open Browser
The application will automatically open at: **http://localhost:8501**

---

## 📖 How to Use

### 1. Upload PDFs
- Click "Browse files" button
- Select up to 10 research papers (PDF format)
- Each file must be under 100 MB

### 2. Process Documents
- Click "🚀 Process Documents" button
- Wait for processing (2-15 minutes depending on size)
- Watch the progress bar

### 3. Review Analysis
- Read the Executive Summary
- Explore the detailed analysis sections
- Check the statistics

### 4. Download Report
- Click "🚀 Generate PDF Report"
- Customize the title if desired
- Click "⬇️ Download Report"
- Save the professional PDF report

---

## ✅ Verification Checklist

Before using, verify everything is working:

```bash
python3 verify_setup.py
```

You should see:
```
🎉 All checks passed! Application is ready to run.
```

---

## 🔐 Security Status

✅ **API Key Protected**
- Stored in `.env` file
- Not tracked by Git
- Not hardcoded anywhere

✅ **Git Safe**
- `.env` in `.gitignore`
- No sensitive data in code
- Ready to commit safely

---

## 💰 Cost Estimate

**Per Analysis:**
- 10 PDFs (50 pages each): $1-2 with caching
- Processing time: 5-10 minutes

**Monthly Usage (50 analyses):**
- API costs: $50-100
- Hosting: FREE (local) or $20+ (cloud)

---

## 🐛 Troubleshooting

### Application Won't Start
```bash
# Install dependencies
pip3 install -r requirements.txt

# Verify setup
python3 verify_setup.py
```

### "API Key Not Found"
- Check `.env` file exists
- Verify `ANTHROPIC_API_KEY` is set
- No spaces around the `=` sign

### Slow Processing
- Normal for large documents
- Be patient (up to 15 minutes)
- Check internet connection

### Check Logs
```bash
tail -f logs/app_*.log
```

---

## 📚 Documentation

- **Quick Start**: This file
- **Full Guide**: `README.md`
- **Deployment**: `DEPLOYMENT.md`
- **Project Status**: `PROJECT_COMPLETE.md`

---

## 🎯 What's Next?

### First Time Users
1. ✅ Run verification script
2. ✅ Start the application
3. ⏳ Upload 1-2 sample PDFs
4. ⏳ Review the generated report
5. ⏳ Test with your research papers

### Ready for Production
- Deploy to Streamlit Cloud (easiest)
- Or deploy to AWS (more control)
- See `DEPLOYMENT.md` for instructions

---

## 💡 Tips

- **Start Small**: Test with 1-2 PDFs first
- **Be Patient**: Processing takes time (especially first run)
- **Check Quality**: Review the first report carefully
- **Save Costs**: Use prompt caching (already enabled)
- **Monitor Usage**: Check Claude API dashboard

---

## ⚡ Quick Commands

```bash
# Start application
./start.sh

# Or manually
streamlit run app.py

# Verify setup
python3 verify_setup.py

# Check logs
tail -f logs/app_*.log

# Stop application
# Press Ctrl+C in terminal
```

---

## 📞 Need Help?

1. Run: `python3 verify_setup.py`
2. Check: `logs/app_*.log`
3. Review: Error messages in UI
4. Read: `README.md` for details

---

**Your AI Research Assistant is Ready!** 🎓

**Start now:** `./start.sh`

**URL:** http://localhost:8501

---

*All systems operational ✅*
