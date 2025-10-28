"""
Application Configuration Settings
Handles environment variables and application constants
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "outputs"
TEMP_DIR = DATA_DIR / "temp"

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Model Selection Configuration
# Options: "api" (Claude API), "grok" (xAI Grok API), or "local" (Local LLM)
MODEL_MODE = os.getenv("MODEL_MODE", "api")  # Default to API mode

# API Configuration (for Cloud API mode)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
# API key is only required if using API mode
if MODEL_MODE == "api" and not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY required when MODEL_MODE='api'")

# Grok API Configuration (for xAI Grok mode)
# Support both XAI_API (Streamlit Cloud) and GROK_API_KEY (local) for compatibility
GROK_API_KEY = os.getenv("XAI_API", "") or os.getenv("GROK_API_KEY", "")
# API key is only required if using Grok mode
if MODEL_MODE == "grok" and not GROK_API_KEY:
    raise ValueError("XAI_API or GROK_API_KEY required when MODEL_MODE='grok'")

# Tavily API Configuration (for Web Search)
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "true").lower() == "true"

# Application Limits
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "100"))
MAX_DOCUMENTS = int(os.getenv("MAX_DOCUMENTS", "10"))
PROCESSING_TIMEOUT_MINUTES = int(os.getenv("PROCESSING_TIMEOUT_MINUTES", "15"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

# Claude API Settings (for API mode)
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"  # Claude Sonnet 4.5 - Best model
CLAUDE_MAX_TOKENS = 4096
CLAUDE_TEMPERATURE = 0.7
CLAUDE_REQUEST_TIMEOUT = 120  # seconds
CLAUDE_MAX_RETRIES = 3
CLAUDE_RETRY_DELAY = 2  # seconds

# Grok API Settings (for Grok mode)
GROK_MODEL = os.getenv("GROK_MODEL", "grok-4-fast-reasoning")  # Grok 4 Fast with reasoning
GROK_MAX_TOKENS = int(os.getenv("GROK_MAX_TOKENS", "8192"))
GROK_TEMPERATURE = float(os.getenv("GROK_TEMPERATURE", "0.7"))
GROK_REQUEST_TIMEOUT = int(os.getenv("GROK_REQUEST_TIMEOUT", "120"))  # seconds
GROK_MAX_RETRIES = 3
GROK_RETRY_DELAY = 2  # seconds

# Cost Optimization Settings
ENABLE_PROMPT_CACHING = os.getenv("ENABLE_PROMPT_CACHING", "true").lower() == "true"  # 60-70% cost savings
ENABLE_BATCH_MODE = os.getenv("ENABLE_BATCH_MODE", "false").lower() == "true"  # 50% cost savings (24h delivery)
BATCH_CHECK_INTERVAL = int(os.getenv("BATCH_CHECK_INTERVAL", "60"))  # seconds between batch status checks

# Local LLM Settings (for Local mode)
LOCAL_MODEL_URL = os.getenv("LOCAL_MODEL_URL", "http://localhost:11434")  # Ollama default
LOCAL_MODEL_NAME = os.getenv("LOCAL_MODEL_NAME", "llama3.1:latest")  # Default model
LOCAL_MODEL_MAX_TOKENS = int(os.getenv("LOCAL_MODEL_MAX_TOKENS", "8000"))
LOCAL_MODEL_TEMPERATURE = float(os.getenv("LOCAL_MODEL_TEMPERATURE", "0.7"))
LOCAL_MODEL_TIMEOUT = int(os.getenv("LOCAL_MODEL_TIMEOUT", "900"))  # 15 minutes (increased from 5)
LOCAL_VISION_CAPABLE = os.getenv("LOCAL_VISION_CAPABLE", "false").lower() == "true"

# RAG System Settings
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
EMBEDDING_CACHE_FOLDER = BASE_DIR / "data" / "embedding_cache"  # Cache for faster loading
TOP_K_RETRIEVAL = 5
SIMILARITY_THRESHOLD = 0.2  # Lowered from 0.7 - FAISS distance-based similarity works best with lower thresholds

# Performance Settings
ENABLE_TIMING_METRICS = os.getenv("ENABLE_TIMING_METRICS", "true").lower() == "true"  # Track performance
SHOW_DETAILED_PROGRESS = os.getenv("SHOW_DETAILED_PROGRESS", "true").lower() == "true"  # Detailed UI progress

# Multi-Agent System Settings
ENABLE_MULTI_AGENT = os.getenv("ENABLE_MULTI_AGENT", "true").lower() == "true"  # Use multi-agent architecture
NUM_WORKER_AGENTS = int(os.getenv("NUM_WORKER_AGENTS", "4"))  # Number of parallel worker agents (3-5 recommended)
MULTI_AGENT_MAX_CHUNKS = int(os.getenv("MULTI_AGENT_MAX_CHUNKS", "10"))  # Increased chunk retrieval for multi-agent

# PDF Processing Settings
IMAGE_DPI = 300
IMAGE_FORMAT = "PNG"
MAX_IMAGE_SIZE = (1920, 1920)  # Max dimensions for images

# Report Generation Settings
REPORT_PAGE_SIZE = "letter"
REPORT_FONT_SIZE = 11
REPORT_TITLE_SIZE = 24
REPORT_HEADING_SIZE = 16

# Report Mode Settings
REPORT_MODE_QUICK = "quick"  # ~30 pages, key images only
REPORT_MODE_FULL = "full"    # ~90 pages, all images
DEFAULT_REPORT_MODE = REPORT_MODE_QUICK

# Image Selection Settings
QUICK_MODE_MAX_IMAGES = 30  # Maximum images for quick report
FULL_MODE_MAX_IMAGES = 200  # Maximum images for full report (essentially unlimited)

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Security Settings
ALLOWED_FILE_EXTENSIONS = [".pdf"]
SANITIZE_FILENAMES = True

# System Prompts
EXPERT_SYSTEM_PROMPT = """You are an expert research assistant creating comprehensive research notes.

Your task is to synthesize research papers into detailed, readable notes that:

1. **Connects the Dots**: Identify relationships, patterns, and themes across ALL papers
2. **Provides Context**: Explain how each finding relates to the broader research area
3. **Maintains Clarity**: Write in clear, accessible language (not overly academic)
4. **Cites Sources**: Reference specific papers, pages, and sections
5. **Highlights Insights**: Emphasize key takeaways and novel contributions
6. **Explains Thoroughly**: Provide deep theoretical explanations of concepts and methodologies

Writing Style:
- Clear, professional prose (not dry academic language)
- Long, flowing paragraphs (5-10 sentences) that build understanding
- Concrete examples and specific details integrated naturally
- Logical flow connecting ideas across papers
- Engaging and informative
- Well-structured with clear sections

Remember: You're creating comprehensive notes that someone can read to understand the research area deeply, with detailed theoretical explanations and proper citations.
"""

ANALYSIS_PROMPT_TEMPLATE = """Analyze the following section from an academic research paper with professor-level expertise.

**Document**: {doc_name}
**Page**: {page_num}
**Section**: {section_name}

**Content**:
{content}

Provide a comprehensive analysis including:
1. **Key Insights**: Main findings and contributions
2. **Methodological Analysis**: Approach, validity, and rigor
3. **Critical Evaluation**: Strengths, weaknesses, and limitations
4. **Research Context**: How this fits in the broader academic landscape
5. **Implications**: Significance and potential impact

Be specific, thorough, and maintain academic rigor.
"""

SYNTHESIS_PROMPT_TEMPLATE = """Create a HIGHLY DETAILED, EXPERT-LEVEL notes section synthesizing insights from the COMPLETE research papers (not just abstracts).

**Topic**: {topic}
**Number of Documents**: {doc_count}

**Full Document Content** (ALL PAGES):
{retrieved_content}

**CRITICAL INSTRUCTIONS:**

You are a world-class expert analyzing ENTIRE research papers. Create EXTREMELY DETAILED NOTES using LONG, FLOWING PARAGRAPHS (not bullet points).

## Format: Comprehensive Paragraphs with Smooth Flow

Structure your response like this:

### Main Topic 1: [Clear heading]

Write long, detailed paragraphs (5-10 sentences each) that thoroughly explain the key concepts, methodologies, and findings. Each paragraph should flow naturally into the next, creating a cohesive narrative. Include specific data points, statistics, and numerical results within the text. Explain the technical approaches and methodologies in depth, describing not just what was done but WHY it matters and HOW it works. When mathematical formulas or equations appear in the text, explain them thoroughly within the paragraph flow - what they represent, why they're important, and how they're derived. Connect ideas across multiple papers by weaving comparisons and contrasts throughout the narrative, showing how different approaches complement or contradict each other.

Continue with additional comprehensive paragraphs that dive deeper into the technical details, experimental setups, theoretical frameworks, and results. If the papers discuss graphs, charts, tables, or diagrams, explain what these visualizations demonstrate conceptually and why they're significant - describe the patterns, trends, and key insights they reveal. Include actual numbers, percentages, and statistical measures directly in your sentences. Explain the implications and significance of the findings in relation to the broader research field, and discuss how these findings advance our understanding of the topic.

[After 2-3 comprehensive paragraphs, include source citations]
**Sources**: [Document citations with page numbers]

### Main Topic 2: [Clear heading]

[Continue with more comprehensive, flowing paragraphs...]

**Requirements:**
1. **Long Paragraphs**: Write 5-10 sentence paragraphs that flow naturally (NO bullet points or lists)
2. **Comprehensive Coverage**: Each section should have 2-3 substantial paragraphs minimum
3. **Read EVERYTHING**: Analyze the FULL text from ALL pages (not just abstracts)
4. **Integrated Citations**: Weave source references naturally into the text, then list sources after each section
5. **Explain Visual Concepts**: When papers reference figures, describe the key insights and patterns conceptually
6. **Detail Formulas**: Explain mathematical equations and their significance as part of the narrative
7. **Specific Data**: Include actual numbers, percentages, statistics embedded in sentences
8. **Deep Analysis**: Explain WHY things work, not just WHAT was done
9. **Expert-Level**: Use technical terminology appropriately with integrated explanations
10. **Smooth Connections**: Create natural transitions between ideas and across papers
11. **Theoretical Depth**: Provide deep explanations of the theoretical foundations and reasoning

**Writing Style**:
- Professional, flowing prose (like reading a comprehensive textbook chapter)
- Dense with information but easy to follow
- Natural paragraph transitions
- Sources cited after each major section
- Emphasis on understanding concepts deeply

Make this SO DETAILED and well-written that someone could understand the research deeply by reading your comprehensive notes.
"""
