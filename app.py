"""
AI Research Assistant - Main Streamlit Application
Analyzes research papers and generates comprehensive reports with citations
"""

import streamlit as st
from pathlib import Path
import sys
from datetime import datetime
import traceback

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import (
    MAX_DOCUMENTS,
    MAX_UPLOAD_SIZE_MB,
    PROCESSING_TIMEOUT_MINUTES,
    UPLOAD_DIR,
    OUTPUT_DIR,
    TEMP_DIR,
    ENABLE_MULTI_AGENT,
    NUM_WORKER_AGENTS
)
from src.pdf_processor import process_multiple_pdfs
from src.rag_system import RAGSystem
from src.comprehensive_analyzer import ComprehensiveAnalyzer
from src.multi_agent_system import MultiAgentOrchestrator
from src.multi_agent_integration import create_comprehensive_summary_with_routing, should_use_multi_agent
from src.cost_tracker import CostTracker
from src.citation_manager import CitationManager
from src.summary_report_generator import SummaryReportGenerator
from src.document_session import DocumentSession, SessionManager
from src.chatbot import DocumentChatbot
from chatbot_ui import display_chatbot_tab, save_session_after_processing
from utils.file_utils import save_uploaded_file, cleanup_temp_files, get_file_info
from utils.logger import get_logger
from utils.exceptions import (
    ResearchAssistantError,
    PDFProcessingError,
    ClaudeAPIError,
    RateLimitError,
    AuthenticationError,
    FileSizeError,
    FileFormatError
)

logger = get_logger(__name__)

# Page configuration
st.set_page_config(
    page_title="AI Research Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #2c3e50;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #7f8c8d;
        text-align: center;
        padding-bottom: 2rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
    }
    .stProgress > div > div > div > div {
        background-color: #3498db;
    }
    </style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize session state variables"""
    if 'processed_files' not in st.session_state:
        st.session_state.processed_files = []
    if 'pdf_data' not in st.session_state:
        st.session_state.pdf_data = None
    if 'rag_system' not in st.session_state:
        st.session_state.rag_system = None
    if 'comprehensive_analyzer' not in st.session_state:
        st.session_state.comprehensive_analyzer = None
    if 'multi_agent_orchestrator' not in st.session_state:
        st.session_state.multi_agent_orchestrator = None
    if 'cost_tracker' not in st.session_state:
        st.session_state.cost_tracker = CostTracker()
    if 'citation_manager' not in st.session_state:
        st.session_state.citation_manager = None
    if 'analysis_complete' not in st.session_state:
        st.session_state.analysis_complete = False
    if 'report_path' not in st.session_state:
        st.session_state.report_path = None
    if 'summary_data' not in st.session_state:
        st.session_state.summary_data = None
    if 'model_mode' not in st.session_state:
        st.session_state.model_mode = 'api'  # Default to API mode
    if 'selected_local_model' not in st.session_state:
        st.session_state.selected_local_model = None  # Will be set when models are loaded
    # Chatbot state
    if 'current_chatbot_session' not in st.session_state:
        st.session_state.current_chatbot_session = None
    if 'chatbot' not in st.session_state:
        st.session_state.chatbot = None
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = None


def reset_session():
    """Reset session state"""
    st.session_state.processed_files = []
    st.session_state.pdf_data = None
    st.session_state.rag_system = None
    st.session_state.analysis_complete = False
    st.session_state.report_path = None
    # Keep analyzer and citation_manager to avoid re-initialization


def display_header():
    """Display application header"""
    st.markdown('<div class="main-header">📚 AI Research Assistant</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Upload research papers and receive professor-level analysis with citations</div>',
        unsafe_allow_html=True
    )


def display_sidebar():
    """Display sidebar with information and settings"""
    with st.sidebar:
        st.header("ℹ️ About")
        st.markdown("""
        This AI-powered research assistant:
        - Analyzes up to 10 PDF research papers
        - Searches web for current information (Tavily AI)
        - Multi-source synthesis (PDF + Web)
        - Extracts key insights with expert-level analysis
        - Generates comprehensive reports with citations
        - Includes images from original documents
        - Provides detailed source references
        """)

        st.header("⚙️ Configuration")

        # Model Selection
        st.subheader("🤖 Model Selection")
        model_mode = st.radio(
            "Choose AI Model:",
            options=["api", "grok", "local"],
            format_func=lambda x: "🌐 Claude API (Cloud)" if x == "api" else ("⚡ Grok 4 Fast (xAI)" if x == "grok" else "💻 Local LLM (Ollama)"),
            index=0,
            help="Choose between Claude API, Grok 4 Fast (98% cheaper), or your local LLM models"
        )

        # Store model mode in session state
        if 'model_mode' not in st.session_state or st.session_state.model_mode != model_mode:
            st.session_state.model_mode = model_mode
            # Clear analyzer to force re-initialization with new mode
            st.session_state.comprehensive_analyzer = None

        # Show model-specific info
        if model_mode == "api":
            st.info("✅ Using Claude Sonnet 4.5 with Vision API")
        elif model_mode == "grok":
            st.info("⚡ Using Grok 4 Fast - 98% cost savings with reasoning capabilities")
        else:
            # Local LLM - show available models
            st.info("💻 Using local LLM (Ollama)")

            # Try to get available models
            try:
                from src.local_llm_handler import get_available_models
                available_models = get_available_models()

                if available_models:
                    # Extract model names
                    model_names = [model.get('name', 'unknown') for model in available_models]

                    # Get model sizes for display
                    model_info = {
                        model.get('name', 'unknown'): f"{model.get('size', 0) / 1e9:.1f}GB"
                        for model in available_models
                    }

                    # Show model selector
                    st.subheader("📦 Select Model")

                    # Get current selection or default
                    current_model = st.session_state.get('selected_local_model', model_names[0] if model_names else 'llama3.1:latest')

                    # Ensure current model is in the list
                    if current_model not in model_names and model_names:
                        current_model = model_names[0]

                    # Model selector with size info
                    selected_model = st.selectbox(
                        "Available Models:",
                        options=model_names,
                        index=model_names.index(current_model) if current_model in model_names else 0,
                        format_func=lambda x: f"{x} ({model_info.get(x, 'unknown size')})",
                        help="Select which local model to use for analysis"
                    )

                    # Store selection
                    previous_model = st.session_state.get('selected_local_model')
                    if selected_model != previous_model:
                        st.session_state.selected_local_model = selected_model
                        # Clear analyzer to force re-initialization with new model
                        st.session_state.comprehensive_analyzer = None

                        # Only show "switched" message if there was a previous model
                        if previous_model is not None:
                            st.success(f"✅ Switched from {previous_model} to {selected_model}")
                        else:
                            st.info(f"📦 Selected model: {selected_model}")

                    # Show model details
                    selected_model_data = next((m for m in available_models if m.get('name') == selected_model), None)
                    if selected_model_data:
                        with st.expander("ℹ️ Model Details", expanded=False):
                            st.write(f"**Name:** {selected_model}")
                            st.write(f"**Size:** {model_info.get(selected_model, 'unknown')}")
                            if 'modified_at' in selected_model_data:
                                st.write(f"**Modified:** {selected_model_data['modified_at'][:10]}")

                else:
                    st.warning("⚠️ No models found. Please install a model:")
                    st.code("ollama pull llama3.1", language="bash")
                    st.caption("Then restart or refresh the page")
                    # Set default
                    if 'selected_local_model' not in st.session_state:
                        st.session_state.selected_local_model = 'llama3.1:latest'

            except Exception as e:
                st.error(f"❌ Could not connect to Ollama: {str(e)}")
                st.info("📝 Make sure Ollama is running:")
                st.code("ollama serve", language="bash")
                # Set default
                if 'selected_local_model' not in st.session_state:
                    st.session_state.selected_local_model = 'llama3.1:latest'

        st.divider()

        # Report Type Selection
        st.subheader("📄 Report Type")
        report_mode = st.radio(
            "Choose report detail level:",
            options=["quick", "full"],
            format_func=lambda x: "📄 Quick Summary (~30 pages, key images)" if x == "quick" else "📚 Full Detailed Report (~90 pages, all images)",
            index=0,
            help="Quick Summary: Concise with most important images. Full Report: Comprehensive with all images."
        )

        # Store report mode in session state
        if 'report_mode' not in st.session_state or st.session_state.report_mode != report_mode:
            st.session_state.report_mode = report_mode

        # Show report mode info
        if report_mode == "quick":
            st.info("📄 Quick Summary: ~30 pages with 20-30 key images for faster reading")
        else:
            st.info("📚 Full Report: ~90 pages with all images for comprehensive analysis")

        st.divider()

        st.info(f"""
        **Limits:**
        - Max documents: {MAX_DOCUMENTS}
        - Max file size: {MAX_UPLOAD_SIZE_MB} MB
        - Processing timeout: {PROCESSING_TIMEOUT_MINUTES} minutes
        """)

        st.header("📖 How to Use")
        st.markdown("""
        1. Upload up to 10 PDF research papers
        2. Click "Process Documents"
        3. Wait for analysis to complete
        4. Download your comprehensive report
        """)

        if st.button("🗑️ Clear Session", use_container_width=True):
            reset_session()
            cleanup_temp_files(TEMP_DIR)
            st.rerun()

        st.header("📊 System Status")
        if st.session_state.processed_files:
            st.success(f"✅ {len(st.session_state.processed_files)} files uploaded")
        if st.session_state.analysis_complete:
            st.success("✅ Analysis complete")


def upload_documents():
    """Handle document upload"""
    st.header("📤 Upload Research Papers")

    uploaded_files = st.file_uploader(
        f"Upload PDF files (max {MAX_DOCUMENTS} documents)",
        type=['pdf'],
        accept_multiple_files=True,
        help=f"Each file must be under {MAX_UPLOAD_SIZE_MB} MB"
    )

    if uploaded_files:
        if len(uploaded_files) > MAX_DOCUMENTS:
            st.error(f"❌ Too many files! Maximum {MAX_DOCUMENTS} documents allowed.")
            return None

        # Display uploaded files
        st.subheader(f"📁 Uploaded Files ({len(uploaded_files)})")

        saved_paths = []
        errors = []

        for uploaded_file in uploaded_files:
            try:
                # Save file
                file_path = save_uploaded_file(uploaded_file, UPLOAD_DIR)
                file_info = get_file_info(file_path)

                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.text(f"📄 {uploaded_file.name}")
                with col2:
                    st.text(f"{file_info['size_mb']:.2f} MB")
                with col3:
                    st.text("✅")

                saved_paths.append(file_path)

            except (FileSizeError, FileFormatError) as e:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.text(f"📄 {uploaded_file.name}")
                with col2:
                    st.text("")
                with col3:
                    st.text("❌")
                errors.append(f"{uploaded_file.name}: {str(e)}")

        if errors:
            st.error("**Errors:**\n" + "\n".join(f"- {err}" for err in errors))

        if saved_paths:
            st.session_state.processed_files = saved_paths
            return saved_paths

    return None


def process_documents(file_paths):
    """Process uploaded PDF documents"""
    st.header("⚙️ Processing Documents")

    try:
        import time
        start_time = time.time()

        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        timing_text = st.empty()

        # Step 1: Extract content from PDFs
        step_start = time.time()
        status_text.text("📖 Extracting text and images from PDFs...")
        progress_bar.progress(10)

        pdf_data = process_multiple_pdfs(file_paths, extract_images=True)

        if not pdf_data:
            st.error("❌ Failed to process any documents")
            return False

        st.session_state.pdf_data = pdf_data

        # Display extraction summary
        total_pages = sum(d.get('total_pages', 0) for d in pdf_data)
        total_images = sum(d.get('total_images', 0) for d in pdf_data)

        step_time = time.time() - step_start
        status_text.success(
            f"✅ Extracted content from {len(pdf_data)} documents "
            f"({total_pages} pages, {total_images} images) in {step_time:.1f}s"
        )
        timing_text.info(f"⏱️ PDF Extraction: {step_time:.1f}s")
        progress_bar.progress(30)

        # Step 2: Initialize RAG system
        status_text.text("🔍 Initializing document analysis system...")

        if not st.session_state.rag_system:
            st.session_state.rag_system = RAGSystem()

        # Process documents for RAG
        chunk_count = st.session_state.rag_system.process_documents(pdf_data)
        status_text.success(f"✅ Created {chunk_count} searchable chunks")
        progress_bar.progress(50)

        # Step 3: Initialize comprehensive analyzer
        model_mode = st.session_state.get('model_mode', 'api')
        selected_local_model = st.session_state.get('selected_local_model', None)

        # For local mode, ensure a model is selected
        if model_mode == "local" and not selected_local_model:
            st.error("❌ Please select a local model from the sidebar before processing")
            return False

        if model_mode == "api":
            model_name = "Claude API"
        elif model_mode == "grok":
            model_name = "Grok 4 Fast"
        else:
            model_name = f"Local LLM ({selected_local_model})" if selected_local_model else "Local LLM"

        status_text.text(f"🤖 Initializing AI analyzer ({model_name})...")

        # Initialize comprehensive analyzer (single-agent)
        if not st.session_state.comprehensive_analyzer:
            try:
                # Pass selected model name for local mode
                st.session_state.comprehensive_analyzer = ComprehensiveAnalyzer(
                    model_mode=model_mode,
                    local_model_name=selected_local_model if model_mode == "local" else None
                )
            except ClaudeAPIError as e:
                st.error(f"❌ Failed to initialize analyzer: {str(e)}")
                logger.error(f"Analyzer initialization failed: {str(e)}")
                return False

        # Initialize multi-agent orchestrator (if using API mode)
        if model_mode == "api" and should_use_multi_agent(model_mode):
            if not st.session_state.multi_agent_orchestrator:
                try:
                    st.session_state.multi_agent_orchestrator = MultiAgentOrchestrator(
                        num_workers=NUM_WORKER_AGENTS
                    )
                    logger.info(f"🚀 Multi-Agent Orchestrator initialized ({NUM_WORKER_AGENTS} workers)")
                except Exception as e:
                    st.warning(f"⚠️  Multi-agent initialization failed, falling back to single-agent: {str(e)}")
                    logger.warning(f"Multi-agent init failed: {str(e)}")
                    st.session_state.multi_agent_orchestrator = None

        if not st.session_state.citation_manager:
            st.session_state.citation_manager = CitationManager()

        # Display which system is being used
        if should_use_multi_agent(model_mode) and st.session_state.multi_agent_orchestrator:
            status_text.success(f"✅ Multi-Agent Research System ready (1 Lead + {NUM_WORKER_AGENTS} Workers)")
            st.info("🚀 **Using Multi-Agent Architecture** (Opus 4 for planning + Sonnet 4 for execution)")
        else:
            status_text.success(f"✅ Single-Agent analyzer ready ({model_name})")

        progress_bar.progress(60)

        # Step 4: Create comprehensive summary with cross-document synthesis
        if should_use_multi_agent(model_mode) and st.session_state.multi_agent_orchestrator:
            status_text.text("🚀 Multi-Agent Research: Planning and executing parallel analysis...")
            status_text.info("⏳ Lead Agent is decomposing research into subtasks and coordinating worker agents...")
        else:
            status_text.text("🔬 Creating comprehensive summary (analyzing all documents together)...")
            status_text.info("⏳ This will take several minutes as we analyze all documents deeply and extract insights...")

        # Get report mode from session state
        report_mode = st.session_state.get('report_mode', 'quick')

        # Create comprehensive summary using routing (multi-agent or single-agent)
        summary_data = create_comprehensive_summary_with_routing(
            model_mode=model_mode,
            comprehensive_analyzer=st.session_state.comprehensive_analyzer,
            multi_agent_orchestrator=st.session_state.multi_agent_orchestrator,
            rag_system=st.session_state.rag_system,
            documents_data=pdf_data,
            focus_areas=None,  # Use default focus areas
            report_mode=report_mode
        )

        status_text.success(f"✅ Comprehensive summary complete!")

        # Display cost information if multi-agent was used
        if 'total_cost' in summary_data and summary_data.get('total_cost', 0) > 0:
            st.session_state.cost_tracker.display_research_cost(summary_data)

        # Display source diversity information if multi-agent with web search was used
        if 'source_diversity' in summary_data and summary_data['source_diversity']:
            diversity = summary_data['source_diversity']
            st.info(f"""
            📊 **Multi-Source Research Summary:**
            - Total Sources: {diversity['total_sources']}
            - PDF Sources: {diversity['pdf_sources']} documents
            - Web Sources: {diversity['web_sources']} articles
            - Unique Web Domains: {diversity['unique_domains']}
            - Web Coverage: {diversity['web_percentage']:.1f}%
            """)

            if diversity['unique_domains'] > 0:
                with st.expander("🌐 Web Domains Used", expanded=False):
                    for domain in diversity['domains_list']:
                        st.write(f"• {domain}")

        progress_bar.progress(90)

        # Store results
        st.session_state.summary_data = summary_data
        st.session_state.analysis_results = {
            'executive_summary': summary_data.get('executive_summary', ''),
            'detailed_sections': summary_data.get('detailed_sections', []),
            'doc_count': len(pdf_data),
            'total_pages': total_pages,
            'total_images': total_images
        }

        progress_bar.progress(100)
        status_text.success("✅ All processing complete!")

        st.session_state.analysis_complete = True
        return True

    except AuthenticationError as e:
        st.error(f"❌ **Authentication Error**: {str(e)}\n\nPlease check your Claude API key.")
        logger.error(f"Authentication error: {str(e)}")
        return False

    except RateLimitError as e:
        st.error(f"❌ **Rate Limit Exceeded**: {str(e)}\n\nPlease wait and try again.")
        logger.error(f"Rate limit error: {str(e)}")
        return False

    except ClaudeAPIError as e:
        st.error(f"❌ **API Error**: {str(e)}")
        logger.error(f"Claude API error: {str(e)}")
        return False

    except PDFProcessingError as e:
        st.error(f"❌ **PDF Processing Error**: {str(e)}")
        logger.error(f"PDF processing error: {str(e)}")
        return False

    except Exception as e:
        st.error(f"❌ **Unexpected Error**: {str(e)}")
        logger.error(f"Unexpected error: {str(e)}\n{traceback.format_exc()}")
        return False


def display_results():
    """Display comprehensive summary results"""
    if not st.session_state.analysis_complete:
        return

    st.header("📊 Comprehensive Summary")

    results = st.session_state.analysis_results

    # Executive Summary
    with st.expander("📋 Executive Summary", expanded=True):
        st.markdown(results['executive_summary'])

    # Detailed Sections
    detailed_sections = results.get('detailed_sections', [])

    for i, section in enumerate(detailed_sections, 1):
        title = section.get('title', f'Section {i}')
        content = section.get('content', '')
        sources = section.get('sources', [])
        images = section.get('images', [])

        with st.expander(f"📌 {title}", expanded=False):
            st.markdown(content)

            # Show image count
            if images:
                st.info(f"📸 {len(images)} images included from source documents")

            # Show sources
            if sources:
                st.markdown("**📚 Sources Referenced:**")
                # Show unique sources
                unique_docs = {}
                for source in sources:
                    # Handle both string format ("doc.pdf, p.1") and dict format
                    if isinstance(source, str):
                        # Parse string format like "research_paper.pdf, p.1"
                        parts = source.split(',')
                        doc_name = parts[0].strip() if parts else 'Unknown'
                        page = parts[1].strip().replace('p.', '').strip() if len(parts) > 1 else '?'
                    elif isinstance(source, dict):
                        # Handle dictionary format
                        doc_name = source.get('doc_name', 'Unknown')
                        page = source.get('page', '?')
                    else:
                        doc_name = 'Unknown'
                        page = '?'

                    if doc_name not in unique_docs:
                        unique_docs[doc_name] = []
                    unique_docs[doc_name].append(page)

                for doc_name, pages in unique_docs.items():
                    pages_str = ', '.join(map(str, sorted(set(pages))[:5]))
                    if len(set(pages)) > 5:
                        pages_str += "..."
                    st.markdown(f"- **{doc_name}**: Pages {pages_str}")

    # Statistics
    st.subheader("📈 Summary Statistics")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Documents", results['doc_count'])
    with col2:
        st.metric("Total Pages", results['total_pages'])
    with col3:
        st.metric("Images Extracted", results['total_images'])
    with col4:
        st.metric("Summary Sections", len(detailed_sections))


def generate_report():
    """Generate and download comprehensive summary PDF"""
    if not st.session_state.analysis_complete:
        return

    st.header("📄 Generate Summary Document")

    # Report title input
    default_title = f"Research Summary - {datetime.now().strftime('%Y-%m-%d')}"
    report_title = st.text_input("Document Title", value=default_title)

    st.info("📝 Your summary document will include:\n- Executive summary\n- Detailed analysis sections\n- Source citations with page numbers\n- All extracted images with references")

    if st.button("🚀 Generate PDF Summary", type="primary", use_container_width=True):
        try:
            with st.spinner("📄 Creating comprehensive summary document with images and citations..."):
                # Initialize summary report generator
                report_gen = SummaryReportGenerator()

                # Get summary data
                summary_data = st.session_state.summary_data
                pdf_data = st.session_state.pdf_data

                # Generate comprehensive summary report
                report_path = report_gen.generate_summary_report(
                    title=report_title,
                    summary_sections=summary_data.get('detailed_sections', []),
                    documents_data=pdf_data,
                    citation_manager=st.session_state.citation_manager
                )

                st.session_state.report_path = report_path
                st.success(f"✅ Summary document generated: {report_path.name}")

                # Show what's included
                total_sections = len(summary_data.get('detailed_sections', []))
                total_images = sum(len(s.get('images', [])) for s in summary_data.get('detailed_sections', []))
                st.info(f"✨ Your summary includes:\n- {total_sections} detailed sections\n- {total_images} images from source documents\n- Complete citations and references")

        except Exception as e:
            st.error(f"❌ Failed to generate summary document: {str(e)}")
            logger.error(f"Report generation failed: {str(e)}\n{traceback.format_exc()}")

    # Download button
    if st.session_state.report_path and st.session_state.report_path.exists():
        with open(st.session_state.report_path, "rb") as f:
            st.download_button(
                label="⬇️ Download Summary Document (PDF)",
                data=f,
                file_name=st.session_state.report_path.name,
                mime="application/pdf",
                use_container_width=True,
                type="primary"
            )

    # Return report path for session saving
    return st.session_state.report_path if st.session_state.report_path else None


def main():
    """Main application with tabbed interface"""
    try:
        # Initialize
        initialize_session_state()

        # Display UI
        display_header()
        display_sidebar()

        # File uploader (outside tabs for better accessibility)
        file_paths = upload_documents()

        # Main content with tabs
        tab1, tab2 = st.tabs(["📄 Process Documents", "💬 Chat with Documents"])

        with tab1:
            # Process Documents workflow
            if file_paths and not st.session_state.analysis_complete:
                st.markdown("---")
                if st.button("🚀 Process Documents", type="primary", use_container_width=True):
                    with st.spinner("Processing documents..."):
                        success = process_documents(file_paths)

                    if success:
                        st.rerun()

            if st.session_state.analysis_complete:
                st.markdown("---")
                display_results()
                st.markdown("---")

                # Generate report
                summary_pdf_path = generate_report()

                if summary_pdf_path and file_paths:
                    # Save to session
                    st.markdown("---")
                    st.subheader("💾 Save to Session")

                    session_name = st.text_input(
                        "Session Name (optional):",
                        value=f"Research - {len(file_paths)} docs",
                        help="Give this session a memorable name for later reference"
                    )

                    if st.button("💾 Save Session for Chat", type="primary"):
                        with st.spinner("Saving session..."):
                            session = save_session_after_processing(
                                pdf_paths=file_paths,
                                summary_pdf_path=summary_pdf_path,
                                session_name=session_name
                            )

                            if session:
                                st.success(f"✅ Session saved! You can now chat with these documents in the 'Chat with Documents' tab.")
                                st.balloons()

        with tab2:
            display_chatbot_tab()

    except Exception as e:
        st.error(f"❌ Application Error: {str(e)}")
        logger.error(f"Application error: {str(e)}\n{traceback.format_exc()}")

        if st.button("🔄 Restart Application"):
            reset_session()
            st.rerun()


if __name__ == "__main__":
    main()
