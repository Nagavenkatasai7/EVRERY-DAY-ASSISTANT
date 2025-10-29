# Streamlit Cloud Deployment Guide

## Pre-Deployment Checklist

### 1. Required API Keys for Streamlit Cloud

You need to add these environment variables in Streamlit Cloud **Secrets Management** (Settings → Secrets):

```toml
# Core AI Model APIs (Choose at least ONE)
ANTHROPIC_API_KEY = "your_anthropic_api_key_here"
GROK_API_KEY = "your_grok_api_key_here"  # Optional: For Grok 4 Fast model
XAI_API = "your_xai_api_key_here"  # Alternative to GROK_API_KEY

# Model Configuration
MODEL_MODE = "api"  # Options: "api" (Claude), "grok" (Grok 4 Fast), "local" (Ollama - not recommended for cloud)

# Resume Maker Research APIs (Choose ONE)
TAVILY_API_KEY = "your_tavily_api_key_here"  # Recommended for cloud deployment
PERPLEXITY_API_KEY = "your_perplexity_api_key_here"  # Alternative to Tavily
RESUME_RESEARCH_API = "tavily"  # Options: "tavily" or "perplexity"

# Local LLM (Only if using MODEL_MODE = "local" - NOT recommended for cloud)
LOCAL_MODEL_URL = "http://localhost:11434"
LOCAL_MODEL_NAME = "llama3.1:latest"

# Social Media OAuth (CRITICAL - See LinkedIn OAuth Fix below)
LINKEDIN_CLIENT_ID = "your_linkedin_client_id"
LINKEDIN_CLIENT_SECRET = "your_linkedin_client_secret"
LINKEDIN_REDIRECT_URI = "https://your-app-name.streamlit.app/"  # MUST match your Streamlit Cloud URL

# Twitter OAuth (Optional)
TWITTER_CLIENT_ID = "your_twitter_client_id"
TWITTER_CLIENT_SECRET = "your_twitter_client_secret"
TWITTER_REDIRECT_URI = "https://your-app-name.streamlit.app/"

# Resume Maker Configuration
GROK_MODEL = "grok-4-fast-reasoning"  # If using Grok
GROK_MAX_TOKENS = "8192"
GROK_TEMPERATURE = "0.7"
```

---

## LinkedIn OAuth Fix (CRITICAL)

### Problem
LinkedIn OAuth login fails because the redirect URL doesn't match between your LinkedIn app settings and the Streamlit Cloud deployment.

### Solution Steps

1. **Get Your Streamlit Cloud URL**
   - Deploy your app to Streamlit Cloud first
   - Your URL will be: `https://your-app-name.streamlit.app/`
   - Example: `https://everyday-assistant.streamlit.app/`

2. **Update LinkedIn Developer App Settings**
   - Go to: https://www.linkedin.com/developers/apps
   - Select your app
   - Go to "Auth" tab
   - Under "OAuth 2.0 settings", add to **Redirect URLs**:
     ```
     https://your-app-name.streamlit.app/
     https://your-app-name.streamlit.app
     ```
   - Add BOTH versions (with and without trailing slash)
   - Click "Update"

3. **Update Streamlit Secrets**
   - In Streamlit Cloud, go to: App Settings → Secrets
   - Update:
     ```toml
     LINKEDIN_REDIRECT_URI = "https://your-app-name.streamlit.app/"
     ```
   - Make sure the URL EXACTLY matches what you added in LinkedIn Dev Console

4. **Redeploy Your App**
   - Streamlit Cloud will automatically redeploy when secrets change
   - Test the LinkedIn login

### Common LinkedIn OAuth Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| "redirect_uri_mismatch" | URLs don't match | Ensure exact match (including trailing slash) |
| "Unauthorized" | Wrong credentials | Verify CLIENT_ID and CLIENT_SECRET in secrets |
| "Page doesn't load" | Wrong redirect URI | Use the Streamlit Cloud URL, not localhost |
| "Invalid scope" | Permissions not granted | In LinkedIn app, enable r_liteprofile and w_member_social scopes |

---

## Twitter OAuth Fix (If Applicable)

If using Twitter/X integration:

1. Go to: https://developer.twitter.com/en/portal/dashboard
2. Select your app → "User authentication settings"
3. Add Callback URL: `https://your-app-name.streamlit.app/`
4. Add Website URL: `https://your-app-name.streamlit.app`
5. Update `TWITTER_REDIRECT_URI` in Streamlit secrets

---

## Deployment Steps

### 1. Push to GitHub (Already Done)
```bash
git add .
git commit -m "Prepare for Streamlit Cloud deployment"
git push origin main
```

### 2. Deploy to Streamlit Cloud

1. Go to: https://share.streamlit.io/
2. Click "New app"
3. Select your GitHub repository: `Nagavenkatasai7/EVRERY-DAY-ASSISTANT`
4. Main file path: `app.py`
5. Click "Advanced settings"
6. Choose Python version: `3.11` or `3.12`
7. Click "Deploy"

### 3. Add Secrets

1. Once deployed, go to: App menu (⋮) → Settings → Secrets
2. Copy-paste all the API keys from above (in TOML format)
3. Click "Save"
4. App will automatically redeploy

---

## API Key Sources

### Where to Get API Keys

| Service | URL | Notes |
|---------|-----|-------|
| **Anthropic (Claude)** | https://console.anthropic.com/ | Required for Claude AI model |
| **Grok (xAI)** | https://console.x.ai/ | Optional, for Grok 4 Fast model |
| **Tavily** | https://tavily.com/ | Recommended for Resume Maker research |
| **Perplexity** | https://www.perplexity.ai/settings/api | Alternative research API |
| **LinkedIn** | https://www.linkedin.com/developers/apps | For social media posting |
| **Twitter** | https://developer.twitter.com/ | For Twitter/X posting |

---

## Model Selection for Cloud Deployment

### Recommended: Claude API (Anthropic)
```toml
MODEL_MODE = "api"
ANTHROPIC_API_KEY = "your_key_here"
```

**Pros:**
- ✅ Best performance
- ✅ Reliable cloud deployment
- ✅ No infrastructure needed

### Alternative: Grok 4 Fast (xAI)
```toml
MODEL_MODE = "grok"
GROK_API_KEY = "your_key_here"
```

**Pros:**
- ✅ 98% cheaper than Claude
- ✅ Fast reasoning
- ✅ Good for high-volume usage

### ⚠️ NOT Recommended for Cloud: Local LLM
```toml
MODEL_MODE = "local"
```

**Why NOT:**
- ❌ Streamlit Cloud doesn't support Ollama
- ❌ Requires local model files (too large)
- ❌ Only works on your local machine

---

## Testing After Deployment

### 1. Test Core Functionality
- ✅ App loads without errors
- ✅ AI Model selection works
- ✅ Resume Maker generates resumes
- ✅ Job Analyzer analyzes job descriptions

### 2. Test OAuth Integrations
- ✅ LinkedIn login button appears
- ✅ Click LinkedIn login → redirects to LinkedIn
- ✅ After LinkedIn authorization → redirects back to app
- ✅ Shows "Connected to LinkedIn" status

### 3. Test API Integrations
- ✅ Tavily/Perplexity research works
- ✅ Resume generation completes successfully
- ✅ No "API key missing" errors

---

## Troubleshooting

### App Won't Start
**Check:**
1. View Streamlit logs (App menu → Manage app → Logs)
2. Verify all required secrets are added
3. Check for typos in secret keys
4. Ensure requirements.txt is up to date

### LinkedIn OAuth Fails
**Fix:**
1. Verify `LINKEDIN_REDIRECT_URI` exactly matches Streamlit Cloud URL
2. Check LinkedIn app has correct redirect URLs (with trailing slash)
3. Verify CLIENT_ID and CLIENT_SECRET are correct
4. Clear browser cache and try again

### "Module not found" Errors
**Fix:**
1. Check requirements.txt includes the missing module
2. Redeploy the app
3. Check Streamlit Cloud logs for build errors

### Resume Generation Fails
**Check:**
1. Verify ANTHROPIC_API_KEY or GROK_API_KEY is correct
2. Check API key has sufficient credits
3. Verify MODEL_MODE matches the API key you provided
4. Check Streamlit logs for specific error messages

---

## Post-Deployment Checklist

- [ ] App deployed successfully to Streamlit Cloud
- [ ] All secrets added in Streamlit Cloud settings
- [ ] LinkedIn redirect URI updated in LinkedIn Developer Portal
- [ ] LinkedIn redirect URI updated in Streamlit secrets
- [ ] LinkedIn OAuth login tested and working
- [ ] Resume generation tested with sample job description
- [ ] Job analysis tested
- [ ] No errors in Streamlit Cloud logs
- [ ] App accessible at your Streamlit Cloud URL

---

## Monitoring and Maintenance

### View Logs
- Go to: Streamlit Cloud → Your app → Manage app → Logs
- Monitor for errors or warnings

### Update Secrets
- Go to: Streamlit Cloud → Your app → Settings → Secrets
- Edit secrets → Save → App auto-redeploys

### Redeploy
- Streamlit Cloud auto-redeploys on every GitHub push
- Manual redeploy: App menu → Reboot app

---

## Support

If you encounter issues:

1. **Check Streamlit Logs**: Most errors are visible in logs
2. **Check LinkedIn Developer Console**: For OAuth issues
3. **Verify API Keys**: Ensure all keys are valid and have credits
4. **Test Locally First**: Run `streamlit run app.py` locally to debug

---

## Security Notes

1. **Never commit .env files** to GitHub
2. **Use Streamlit Secrets** for all API keys
3. **Rotate keys regularly** for security
4. **Use HTTPS** (automatic with Streamlit Cloud)
5. **Enable 2FA** on your Streamlit Cloud account

---

**Last Updated:** October 29, 2025
**Deployment Status:** ✅ Ready for Production
