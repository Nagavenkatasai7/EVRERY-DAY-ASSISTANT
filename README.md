# AI Research Assistant

A production-ready AI-powered research assistant that analyzes academic PDF papers and generates comprehensive reports with professor-level insights, citations, and extracted images.

## Features

- **Multi-Document Analysis**: Process up to 10 PDF research papers simultaneously
- **AI-Powered Insights**: Claude Sonnet 4.5 provides expert-level analysis
- **Citation Tracking**: Automatic citation generation linking to source documents
- **Image Extraction**: Extracts and includes images from original PDFs
- **Professional Reports**: Generates publication-quality PDF reports
- **RAG System**: Advanced retrieval-augmented generation for accurate analysis
- **Secure**: API keys protected with environment variables
- **Error Handling**: Comprehensive error handling and recovery

## Technology Stack

- **Frontend**: Streamlit
- **AI Model**: Claude Sonnet 4.5 API
- **PDF Processing**: PyMuPDF (fitz)
- **Document Analysis**: LangChain + FAISS
- **Embeddings**: sentence-transformers
- **PDF Generation**: ReportLab
- **Python**: 3.8+

## Installation

### Prerequisites

- Python 3.8 or higher
- Claude API key from Anthropic

### Setup Steps

1. **Clone or navigate to the project directory**
   ```bash
   cd research-assistant
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**

   The `.env` file is already configured with your API key. Verify it contains:
   ```
   ANTHROPIC_API_KEY=your_api_key_here
   MAX_UPLOAD_SIZE_MB=100
   MAX_DOCUMENTS=10
   PROCESSING_TIMEOUT_MINUTES=15
   ```

5. **Run the application**
   ```bash
   streamlit run app.py
   ```

   The application will open in your default browser at `http://localhost:8501`

## Usage

### Quick Start

1. **Upload PDFs**: Click "Browse files" and select up to 10 research papers
2. **Process**: Click "Process Documents" to begin analysis
3. **Review**: Examine the AI-generated insights and analysis
4. **Download**: Generate and download the comprehensive PDF report

### Features Explained

#### Document Processing
- Extracts text and images from all pages
- Identifies sections and structure
- Creates searchable document index

#### AI Analysis
- Generates executive summary
- Analyzes research questions and objectives
- Evaluates methodologies
- Identifies key findings and contributions
- Suggests future research directions
- Identifies relationships between papers

#### Report Generation
- Professional PDF format
- Table of contents
- Detailed analysis sections
- Inline citations
- Bibliography
- Extracted images with captions

## Security

### API Key Protection

- API keys stored in `.env` file (not tracked by Git)
- `.gitignore` configured to prevent credential exposure
- Environment variables used throughout application
- No hardcoded secrets

### Git Safety

Before committing to Git:
1. Verify `.gitignore` is in place
2. Check that `.env` is listed in `.gitignore`
3. Run: `git status` to ensure `.env` is not tracked
4. Never commit with `--force` if `.env` appears

### Best Practices

- Keep `.env` file secure
- Don't share your API key
- Rotate API keys periodically
- Use separate keys for development and production

## Configuration

### Application Limits

Edit `.env` to change:
- `MAX_UPLOAD_SIZE_MB`: Maximum file size per PDF
- `MAX_DOCUMENTS`: Maximum number of PDFs to process
- `PROCESSING_TIMEOUT_MINUTES`: Maximum processing time

### Advanced Settings

Edit `config/settings.py` to customize:
- Chunk size for document splitting
- Embedding model
- Claude model parameters
- Report styling

## Directory Structure

```
research-assistant/
├── app.py                    # Main Streamlit application
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (PROTECTED)
├── .gitignore               # Git ignore rules
├── README.md                # This file
├── config/
│   └── settings.py          # Application configuration
├── src/
│   ├── pdf_processor.py     # PDF extraction
│   ├── rag_system.py        # RAG implementation
│   ├── claude_analyzer.py   # Claude API integration
│   ├── citation_manager.py  # Citation tracking
│   └── report_generator.py  # PDF report generation
├── utils/
│   ├── logger.py            # Logging utilities
│   ├── exceptions.py        # Custom exceptions
│   ├── file_utils.py        # File handling
│   └── image_utils.py       # Image processing
└── data/
    ├── uploads/             # Uploaded PDFs
    ├── outputs/             # Generated reports
    └── temp/                # Temporary files
```

## Error Handling

The application includes comprehensive error handling for:

- **File Errors**: Invalid formats, size limits, corrupted PDFs
- **API Errors**: Rate limits, authentication, connection issues
- **Processing Errors**: PDF extraction, embedding generation
- **System Errors**: Memory limits, timeouts

All errors are logged to `logs/app_YYYYMMDD.log`

## Performance

### Processing Time

- **Small documents** (10-20 pages each): 2-5 minutes
- **Medium documents** (50-100 pages each): 5-10 minutes
- **Large documents** (100+ pages each): 10-15 minutes

### Cost Estimation

Claude API costs (approximate):
- **10 PDFs, 50 pages each**: $5-10
- **With prompt caching**: $1-2

## Deployment

### Streamlit Cloud (Recommended for Quick Deploy)

1. Push code to GitHub (without `.env`)
2. Connect Streamlit Cloud to repository
3. Add secrets in Streamlit Cloud dashboard:
   - `ANTHROPIC_API_KEY`
4. Deploy!

### AWS Deployment

See `DEPLOYMENT.md` for detailed AWS deployment instructions.

### Docker Deployment

```dockerfile
# Dockerfile example
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["streamlit", "run", "app.py"]
```

## Troubleshooting

### Common Issues

**Import Errors**
```bash
pip install --upgrade -r requirements.txt
```

**API Key Not Found**
- Verify `.env` file exists
- Check `ANTHROPIC_API_KEY` is set
- Ensure no extra spaces in `.env`

**Memory Errors**
- Reduce `MAX_DOCUMENTS` in `.env`
- Process fewer pages at once
- Increase system RAM

**Slow Processing**
- Normal for large documents
- Enable prompt caching (already configured)
- Reduce image extraction if needed

### Logs

Check logs for detailed error information:
```bash
tail -f logs/app_$(date +%Y%m%d).log
```

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests (when available)
pytest tests/
```

### Code Quality

```bash
# Format code
black src/ utils/ app.py

# Lint code
flake8 src/ utils/ app.py
```

## Limitations

- Maximum 10 documents per analysis
- PDF files only (no DOCX, TXT, etc.)
- English language optimized
- Requires internet connection for API
- Processing time depends on document size

## Future Enhancements

- [ ] Support for more document formats
- [ ] Multi-language support
- [ ] Custom analysis templates
- [ ] Batch processing queue
- [ ] Export to multiple formats (Word, LaTeX)
- [ ] Integration with reference managers
- [ ] Collaborative features

## License

This project is provided as-is for research and educational purposes.

## Support

For issues and questions:
1. Check logs in `logs/` directory
2. Review error messages carefully
3. Verify API key is valid
4. Check Anthropic API status

## Credits

- **AI Model**: Anthropic Claude Sonnet 4.5
- **PDF Processing**: PyMuPDF
- **Document Analysis**: LangChain
- **UI Framework**: Streamlit
- **PDF Generation**: ReportLab

## Version

Current Version: 1.0.0
Last Updated: 2025-01-26

---

**Built with Claude Code** 🚀
