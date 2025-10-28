# 🖥️ Local LLM Support - Complete Guide

## NEW FEATURE: Use Your Own Local Models!

Your AI Research Assistant now supports **both** Cloud API and Local LLM models! You can choose to use:
- **Claude API (Cloud)**: Full vision capabilities, fastest processing
- **Local LLM**: Your own models, no API costs, complete privacy

---

## ✅ What's New

### Flexible Model Selection
- **Switch between modes in the UI** - no config file editing needed
- **API Mode**: Uses Claude Sonnet 4.5 with vision (default)
- **Local Mode**: Uses your local LLM models (Ollama, LlamaCpp, etc.)

### Privacy & Cost Control
- **No API Costs**: Use local models completely free
- **Complete Privacy**: Your data never leaves your machine
- **Offline Capable**: Work without internet connection
- **Your Hardware**: Use your own GPU/CPU resources

### Seamless Integration
- **Same Features**: Full document analysis, citations, PDF generation
- **Same UI**: No changes to user interface
- **Auto-Detection**: System detects which mode you're using
- **Graceful Fallback**: Clear warnings if vision not available

---

## 🚀 Quick Start

### Option 1: Using Claude API (Default)
1. Open the application: http://localhost:8502
2. In the sidebar, keep "🌐 Claude API (Cloud)" selected
3. Upload PDFs and analyze (full vision support)

### Option 2: Using Local LLM
1. **Install Ollama** (if not installed):
   ```bash
   # macOS/Linux
   curl -fsSL https://ollama.ai/install.sh | sh

   # Or download from https://ollama.ai
   ```

2. **Pull a model**:
   ```bash
   # Recommended: Llama 3.1 (8B parameters)
   ollama pull llama3.1

   # Or other models:
   ollama pull llama3.1:70b    # Larger, better quality
   ollama pull mistral          # Alternative model
   ollama pull codellama        # Good for technical content
   ```

3. **Start Ollama server** (if not running):
   ```bash
   ollama serve
   ```

4. **Switch to Local Mode**:
   - Open http://localhost:8502
   - In the sidebar, select "💻 Local LLM (Ollama)"
   - Upload PDFs and analyze!

---

## ⚙️ Configuration

### UI Configuration (Recommended)
**Easiest way** - just use the radio button in the sidebar:
- 🌐 Claude API (Cloud) - for vision capabilities
- 💻 Local LLM (Ollama) - for local processing

### Environment Configuration (Advanced)
Edit `.env` file for persistent settings:

```bash
# Model Selection: "api" or "local"
MODEL_MODE=local  # Change to "local" for default local mode

# Local LLM Settings
LOCAL_MODEL_URL=http://localhost:11434
LOCAL_MODEL_NAME=llama3.1:latest
LOCAL_MODEL_MAX_TOKENS=8000
LOCAL_MODEL_TEMPERATURE=0.7
LOCAL_MODEL_TIMEOUT=300
LOCAL_VISION_CAPABLE=false
```

### Configuration Options Explained

| Setting | Description | Default |
|---------|-------------|---------|
| `MODEL_MODE` | "api" or "local" | `api` |
| `LOCAL_MODEL_URL` | Ollama server URL | `http://localhost:11434` |
| `LOCAL_MODEL_NAME` | Model to use | `llama3.1:latest` |
| `LOCAL_MODEL_MAX_TOKENS` | Max response length | `8000` |
| `LOCAL_MODEL_TEMPERATURE` | Creativity (0.0-1.0) | `0.7` |
| `LOCAL_MODEL_TIMEOUT` | Request timeout (seconds) | `300` (5 min) |
| `LOCAL_VISION_CAPABLE` | Does model support vision? | `false` |

---

## 📊 Feature Comparison

| Feature | Claude API | Local LLM |
|---------|-----------|-----------|
| **Vision Analysis** | ✅ Full support | ❌ Not yet* |
| **Image Extraction** | ✅ Yes | ✅ Yes |
| **Image in PDF** | ✅ Yes | ✅ Yes |
| **Formula Reading** | ✅ From images | ❌ Text only* |
| **Cost** | Pay per token | Free |
| **Speed** | Fast (cloud) | Depends on hardware |
| **Privacy** | Cloud-based | 100% local |
| **Offline** | ❌ Needs internet | ✅ Works offline |
| **Quality** | Excellent | Good (model-dependent) |
| **Setup** | Just API key | Install Ollama |

**Most local LLMs don't support vision yet, but images are still extracted and included in the PDF report.*

---

## 🖼️ Vision Capabilities

### With Claude API (Vision Mode)
- ✅ Analyzes graphs, charts, diagrams
- ✅ Reads mathematical formulas from images
- ✅ Explains what figures show
- ✅ Describes data patterns in visualizations
- ✅ Interprets complex diagrams

### With Local LLM (Text-Only Mode)
- ❌ Cannot analyze image content
- ✅ Images still extracted from PDFs
- ✅ Images included in final PDF report
- ✅ Analyzes all text content comprehensively
- ⚠️ Warning shown: "Images available but not analyzed"

### Future: Vision-Capable Local Models
When vision-capable local models become available (e.g., LLaVA, Bakllava):
```bash
# Example (when available)
LOCAL_VISION_CAPABLE=true
```

---

## 🔧 Advanced Setup

### Using Different Local Models

#### Llama 3.1 (Recommended)
```bash
ollama pull llama3.1
# In .env:
LOCAL_MODEL_NAME=llama3.1:latest
```

#### Larger Models (Better Quality)
```bash
ollama pull llama3.1:70b
# In .env:
LOCAL_MODEL_NAME=llama3.1:70b
```

#### Mistral (Fast Alternative)
```bash
ollama pull mistral
# In .env:
LOCAL_MODEL_NAME=mistral:latest
```

#### CodeLlama (Good for Technical Papers)
```bash
ollama pull codellama
# In .env:
LOCAL_MODEL_NAME=codellama:latest
```

### Custom Ollama URL
If Ollama is on a different machine or port:
```bash
LOCAL_MODEL_URL=http://192.168.1.100:11434  # Different machine
LOCAL_MODEL_URL=http://localhost:8080        # Different port
```

### Performance Tuning

#### For Faster Processing (Lower Quality)
```bash
LOCAL_MODEL_TEMPERATURE=0.5  # Less creative, more focused
LOCAL_MODEL_MAX_TOKENS=4000  # Shorter responses
```

#### For Better Quality (Slower)
```bash
LOCAL_MODEL_TEMPERATURE=0.9  # More creative
LOCAL_MODEL_MAX_TOKENS=12000 # Longer, more detailed
LOCAL_MODEL_TIMEOUT=600      # 10 minutes timeout
```

---

## 🛠️ Troubleshooting

### "Cannot connect to local LLM server"
**Problem**: Ollama not running
**Solution**:
```bash
# Start Ollama
ollama serve

# Or check if running:
ps aux | grep ollama
```

### "Model 'llama3.1' not found"
**Problem**: Model not downloaded
**Solution**:
```bash
# List available models
ollama list

# Pull the model
ollama pull llama3.1
```

### "Local LLM request timed out"
**Problem**: Model too slow or prompt too long
**Solution**:
- Use a smaller model (llama3.1:8b instead of 70b)
- Increase timeout in `.env`:
  ```bash
  LOCAL_MODEL_TIMEOUT=600  # 10 minutes
  ```
- Reduce document count

### Images Not Analyzed
**Expected**: Local LLMs don't support vision (yet)
**Note**:
- Images are still extracted
- Images are included in the PDF report
- Text is fully analyzed
- Switch to Claude API for vision analysis

### Slow Performance
**Solutions**:
1. Use a smaller model:
   ```bash
   ollama pull llama3.1:8b  # 8 billion parameters
   ```

2. Reduce documents:
   - Process fewer PDFs at once
   - Split large documents

3. Hardware:
   - Use GPU if available
   - Close other applications
   - Increase RAM allocation

---

## 💡 When to Use Each Mode

### Use Claude API When:
- ✅ You need vision analysis of images
- ✅ You want formulas read from images
- ✅ You need highest quality analysis
- ✅ You have API credits available
- ✅ You need fastest processing

### Use Local LLM When:
- ✅ You want zero API costs
- ✅ Privacy is critical (data stays local)
- ✅ You're working offline
- ✅ You have good local hardware
- ✅ Text-only analysis is sufficient
- ✅ You're processing many documents regularly

---

## 📈 Cost Comparison

### Claude API
- **Cost**: ~$0.01-$0.05 per document
- **Per 10 papers**: ~$0.10-$0.50
- **Monthly (100 papers)**: ~$1-$5
- **Includes**: Vision analysis, formula reading

### Local LLM
- **Cost**: $0 (free)
- **One-time**: Hardware investment (optional GPU)
- **Ongoing**: Electricity (minimal)
- **Includes**: Text analysis, PDF generation

### Cost Savings Example
If you process 100 papers per month:
- **Claude API**: $1-$5/month
- **Local LLM**: $0/month
- **Annual Savings**: $12-$60

---

## 🔐 Privacy Comparison

### Claude API
- Documents sent to Anthropic servers
- Processed in cloud
- Subject to Anthropic's privacy policy
- Secure, encrypted transmission
- Data not used for training (per policy)

### Local LLM
- Documents never leave your machine
- Processed entirely locally
- Complete control over data
- No external communication
- Perfect for sensitive research

---

## 🎯 Best Practices

### For Research Papers
1. **Start with Claude API** to see full capabilities
2. **Switch to Local** for routine processing
3. **Use API for complex papers** with many formulas
4. **Use Local for text-heavy papers**

### For Privacy-Sensitive Work
1. **Always use Local mode**
2. Disconnect from internet if needed
3. Process confidential documents safely

### For Cost Optimization
1. **Use Local by default**
2. **Switch to API** only when vision needed
3. Batch process multiple papers locally
4. Reserve API for final review

---

## 🔄 Switching Between Modes

### During a Session
1. Go to sidebar in the app
2. Select different model mode
3. System automatically reinitializes
4. Previous documents cleared (for safety)
5. Upload and process again

### Permanent Change
Edit `.env`:
```bash
MODEL_MODE=local  # or "api"
```

---

## 📋 Recommended Workflow

### Workflow 1: Local-First (Cost-Effective)
```
1. Set to Local LLM mode
2. Upload and process 5-10 papers
3. Review text analysis
4. If formulas need analysis, switch to API
5. Reprocess specific papers with API
6. Switch back to Local for next batch
```

### Workflow 2: API-First (Quality-First)
```
1. Set to Claude API mode
2. Upload and process papers
3. Get full vision analysis
4. Export high-quality report
5. Switch to Local for subsequent reviews
```

### Workflow 3: Hybrid (Balanced)
```
1. Quick review with Local LLM
2. Identify papers with important figures
3. Switch to API for those papers only
4. Combine insights from both modes
```

---

## 🚀 Getting Started Checklist

### For Claude API Users:
- [ ] Verify API key in `.env`
- [ ] Select "Claude API" in sidebar
- [ ] Upload PDFs
- [ ] Enjoy full vision analysis!

### For Local LLM Users:
- [ ] Install Ollama: `curl -fsSL https://ollama.ai/install.sh | sh`
- [ ] Pull model: `ollama pull llama3.1`
- [ ] Start server: `ollama serve`
- [ ] Select "Local LLM" in sidebar
- [ ] Upload PDFs
- [ ] Process locally!

---

## 📚 Additional Resources

### Ollama Documentation
- Website: https://ollama.ai
- Models: https://ollama.ai/library
- GitHub: https://github.com/ollama/ollama

### Recommended Models
- **Llama 3.1 (8B)**: Best balance of speed and quality
- **Llama 3.1 (70B)**: Highest quality, needs good GPU
- **Mistral**: Fast, good for quick processing
- **CodeLlama**: Excellent for technical papers

### System Requirements
- **Minimum**: 8GB RAM, CPU processing
- **Recommended**: 16GB RAM, NVIDIA GPU
- **Optimal**: 32GB RAM, NVIDIA RTX 3090/4090

---

## 🎉 Summary

**You now have complete flexibility:**
- ✅ Use Claude API for best quality + vision
- ✅ Use Local LLM for privacy + cost savings
- ✅ Switch anytime in the UI
- ✅ No code changes needed
- ✅ Same great features in both modes

**The choice is yours!** 🚀

---

## 🆘 Need Help?

### Quick Checks:
1. **Ollama installed?** `ollama --version`
2. **Ollama running?** `curl http://localhost:11434`
3. **Model downloaded?** `ollama list`
4. **Port available?** `lsof -i:11434`

### Common Issues:
- **Port conflict**: Change `LOCAL_MODEL_URL`
- **Model not found**: Run `ollama pull <model>`
- **Timeout**: Increase `LOCAL_MODEL_TIMEOUT`
- **Out of memory**: Use smaller model

---

**Application running at: http://localhost:8502**

**Test both modes and choose what works best for you!** 💻
