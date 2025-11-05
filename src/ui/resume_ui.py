"""
Ultra ATS Resume Generator UI
Integrated into Research Assistant
"""
import streamlit as st
import os
import sys
from pathlib import Path
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import resume maker components
from src.database import Database
from src.parsers import ProfileParser
from src.analyzers import JobAnalyzer
from src.resume_utils.research_router import ResearchRouter
from src.generators import ResumeGenerator
from src.generators.pdf_generator import PDFGenerator
from src.generators.coverletter_generator import CoverLetterGenerator
from src.generators.coverletter_pdf_generator import CoverLetterPDFGenerator

from utils.logger import get_logger

logger = get_logger(__name__)


def resume_maker_page():
    """Main resume maker page integrated into research assistant"""

    # Initialize session state
    if 'generated_resume' not in st.session_state:
        st.session_state.generated_resume = None
    if 'job_analysis' not in st.session_state:
        st.session_state.job_analysis = None
    if 'company_research' not in st.session_state:
        st.session_state.company_research = None
    if 'generated_cover_letter' not in st.session_state:
        st.session_state.generated_cover_letter = None
    if 'profile_text' not in st.session_state:
        st.session_state.profile_text = None
    if 'current_job_id' not in st.session_state:
        st.session_state.current_job_id = None

    # Get model selection from GLOBAL session state (shared with main app)
    resume_model_mode = st.session_state.get('model_mode', os.getenv('MODEL_MODE', 'api'))
    resume_research_api = st.session_state.get('resume_research_api', os.getenv('RESUME_RESEARCH_API', 'tavily'))
    resume_local_model = st.session_state.get('selected_local_model', os.getenv('LOCAL_MODEL_NAME', 'llama3.1:latest'))

    # Initialize components
    try:
        db = Database()
        profile_parser = ProfileParser()

        # Pass local model name to components when in local mode
        if resume_model_mode == 'local':
            # Temporarily set environment variable for local model
            original_local_model = os.getenv('LOCAL_MODEL_NAME')
            os.environ['LOCAL_MODEL_NAME'] = resume_local_model

        job_analyzer = JobAnalyzer(model_mode=resume_model_mode)
        research_router = ResearchRouter(research_api=resume_research_api)
        resume_generator = ResumeGenerator(model_mode=resume_model_mode)
        pdf_generator = PDFGenerator()
        coverletter_generator = CoverLetterGenerator()
        coverletter_pdf_generator = CoverLetterPDFGenerator()

        # Restore original environment variable if it was changed
        if resume_model_mode == 'local' and original_local_model:
            os.environ['LOCAL_MODEL_NAME'] = original_local_model

    except Exception as e:
        st.error(f"Failed to initialize resume maker components: {str(e)}")
        logger.error(f"Component initialization error: {str(e)}")
        return

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Resume Maker Settings")

        # Show current model selection (from main app configuration)
        st.info(f"""
        **Using Main App Configuration:**
        - AI Model: {resume_model_mode.upper()}
        {f"- Local Model: {resume_local_model}" if resume_model_mode == 'local' else ""}

        *Configure AI model in the left sidebar "Configuration" section*
        """)

        st.divider()

        # Research API Selection (Resume Maker specific)
        st.subheader("🔍 Research API")
        research_options = {
            'tavily': 'Tavily Search',
            'perplexity': 'Perplexity AI'
        }

        selected_research = st.selectbox(
            "Select Research API",
            options=list(research_options.keys()),
            format_func=lambda x: research_options[x],
            index=list(research_options.keys()).index(resume_research_api),
            key="resume_research_selector",
            help="Choose the API for company research"
        )

        if selected_research != resume_research_api:
            st.session_state.resume_research_api = selected_research
            st.rerun()

        st.divider()

        # Check for Profile.pdf
        profile_path = Path("Profile.pdf")
        profile_exists = profile_path.exists()

        if profile_exists:
            st.success("✓ Profile.pdf found")
        else:
            st.warning("⚠️ Profile.pdf not found")

            st.info("Upload your profile PDF below:")
            uploaded_profile = st.file_uploader(
                "Upload Profile PDF",
                type=["pdf"],
                key="resume_profile_uploader",
                help="Upload your profile/resume PDF for parsing"
            )

            if uploaded_profile:
                # Save to current directory
                with open("Profile.pdf", "wb") as f:
                    f.write(uploaded_profile.read())
                st.success("✓ Profile uploaded successfully!")
                st.rerun()

        # Check API keys based on selected model
        st.divider()
        st.subheader("🔑 API Keys Status")

        if resume_model_mode == 'api':
            if os.getenv("ANTHROPIC_API_KEY"):
                st.success("✓ Anthropic API key configured")
            else:
                st.error("✗ Anthropic API key missing")
        elif resume_model_mode == 'grok':
            grok_key = os.getenv("GROK_API_KEY") or os.getenv("XAI_API")
            if grok_key:
                st.success("✓ Grok API key configured")
            else:
                st.error("✗ Grok API key missing")
        elif resume_model_mode == 'local':
            st.info("ℹ Using Local LLM (no API key needed)")

        # Research API key status
        if selected_research == 'perplexity':
            perplexity_key = os.getenv("PERPLEXITY_API_KEY")
            if perplexity_key and perplexity_key != 'your_perplexity_key_here':
                st.success("✓ Perplexity API key configured")
            else:
                st.warning("⚠️ Perplexity API key not set")
        elif selected_research == 'tavily':
            tavily_key = os.getenv("TAVILY_API_KEY")
            if tavily_key:
                st.success("✓ Tavily API key configured")
            else:
                st.warning("⚠️ Tavily API key not set")

        st.divider()

        # Previous resumes
        st.header("📚 Previous Resumes")
        try:
            previous_resumes = db.get_all_resumes()

            if previous_resumes:
                st.write(f"Total resumes generated: {len(previous_resumes)}")
                for resume in previous_resumes[:5]:
                    with st.expander(f"{resume['company_name']} - {resume['job_title'][:30]}..."):
                        st.write(f"**Created:** {resume['created_at']}")
                        st.write(f"**ATS Score:** {resume['ats_score'] or 'N/A'}")
                        if resume['file_path'] and Path(resume['file_path']).exists():
                            with open(resume['file_path'], 'rb') as f:
                                st.download_button(
                                    "Download",
                                    f.read(),
                                    file_name=Path(resume['file_path']).name,
                                    mime="application/pdf",
                                    key=f"download_prev_{resume['id']}"
                                )
            else:
                st.info("No resumes generated yet")
        except Exception as e:
            st.warning(f"Could not load previous resumes: {str(e)}")

    # Main tabs
    tab1, tab2, tab3 = st.tabs(["🎯 Generate Resume", "📊 Job Analysis", "ℹ️ About"])

    with tab1:
        st.header("Generate ATS-Optimized Resume")

        # Input fields
        col1, col2 = st.columns([2, 1])

        with col1:
            company_name = st.text_input(
                "Company Name *",
                placeholder="e.g., Google, Microsoft, Amazon",
                help="Enter the company name for the job",
                key="resume_company_name"
            )

        with col2:
            job_url = st.text_input(
                "Job URL (optional)",
                placeholder="https://...",
                help="Optional: URL to the job posting",
                key="resume_job_url"
            )

        job_description = st.text_area(
            "Job Description *",
            height=300,
            placeholder="Paste the complete job description here...",
            help="Paste the full job description including requirements, responsibilities, and qualifications",
            key="resume_job_description"
        )

        col1, col2, col3 = st.columns([2, 2, 1])

        with col1:
            use_research = st.checkbox(
                f"Use {research_router.get_api_name()} for company research",
                value=True,
                help="Enhance resume with company-specific insights",
                key="resume_use_research"
            )

        with col2:
            target_score = st.slider(
                "Target ATS Score",
                min_value=85,
                max_value=100,
                value=90,
                help="Target ATS compatibility score",
                key="resume_target_score"
            )

        # Generate button
        if st.button("🚀 Generate ATS-Optimized Resume", type="primary", use_container_width=True, key="resume_generate_btn"):
            if not company_name or not job_description:
                st.error("Please provide both company name and job description")
            elif not profile_path.exists():
                st.error("Profile.pdf not found. Please upload your profile PDF.")
            else:
                # Show progress
                with st.spinner("Generating your ATS-optimized resume..."):
                    try:
                        # Step 1: Parse profile
                        progress_bar = st.progress(0)
                        st.info("📄 Parsing your profile...")
                        profile_text = profile_parser.get_profile_summary()
                        st.session_state.profile_text = profile_text
                        progress_bar.progress(20)

                        # Step 2: Analyze job description
                        st.info("🔍 Analyzing job description...")
                        job_analysis = job_analyzer.analyze_job_description(
                            job_description,
                            company_name
                        )
                        st.session_state.job_analysis = job_analysis
                        progress_bar.progress(40)

                        # Step 3: Company research (if enabled)
                        company_research = None
                        if use_research:
                            st.info(f"🔬 Researching company with {research_router.get_api_name()}...")
                            company_research = research_router.research_company(
                                company_name,
                                job_analysis.get('job_title')
                            )
                            st.session_state.company_research = company_research
                        progress_bar.progress(60)

                        # Step 4: Check for duplicates
                        st.info("🔎 Checking for existing resumes...")
                        job_id = db.insert_job_description(
                            company_name,
                            job_description,
                            job_analysis.get('job_title'),
                            job_url,
                            json.dumps(job_analysis.get('keywords', []))
                        )
                        st.session_state.current_job_id = job_id

                        existing_resume = db.check_resume_exists(job_id)
                        if existing_resume:
                            st.warning(f"⚠️ Resume already exists for this job (created {existing_resume['created_at']})")

                        progress_bar.progress(70)

                        # Step 5: Generate resume
                        st.info("✨ Generating ATS-optimized resume with Claude...")
                        resume_result = resume_generator.generate_resume(
                            profile_text,
                            job_analysis,
                            company_research
                        )

                        if not resume_result['success']:
                            st.error(f"Resume generation failed: {resume_result.get('error', 'Unknown error')}")
                            return

                        progress_bar.progress(90)

                        # Step 6: Generate PDF
                        st.info("📝 Creating PDF...")
                        output_dir = Path("generated_resumes")
                        output_dir.mkdir(exist_ok=True)

                        # Create filename
                        safe_company_name = "".join(c for c in company_name if c.isalnum() or c in (' ', '-', '_')).strip()
                        pdf_filename = f"Resume_{safe_company_name}.pdf"
                        pdf_path = output_dir / pdf_filename

                        pdf_generator.markdown_to_pdf(resume_result['content'], str(pdf_path))
                        progress_bar.progress(95)

                        # Step 7: Save to database
                        db.insert_generated_resume(
                            job_id,
                            resume_result['content'],
                            str(pdf_path),
                            target_score
                        )

                        progress_bar.progress(100)

                        # Success!
                        st.success("✅ ATS-Optimized Resume Generated Successfully!")
                        st.balloons()

                        # Store in session
                        st.session_state.generated_resume = {
                            'content': resume_result['content'],
                            'pdf_path': str(pdf_path),
                            'company_name': company_name
                        }

                    except Exception as e:
                        st.error(f"Error generating resume: {e}")
                        import traceback
                        st.code(traceback.format_exc())

        # Display generated resume
        if st.session_state.generated_resume:
            st.divider()
            st.subheader("📄 Generated Resume")

            col1, col2 = st.columns([3, 1])

            with col1:
                with st.expander("📝 Resume Content (Markdown)", expanded=True):
                    st.markdown(st.session_state.generated_resume['content'])

            with col2:
                st.metric("Target ATS Score", f"{target_score}+")

                # Download button
                pdf_path = st.session_state.generated_resume['pdf_path']
                if Path(pdf_path).exists():
                    with open(pdf_path, 'rb') as f:
                        st.download_button(
                            "⬇️ Download PDF",
                            f.read(),
                            file_name=Path(pdf_path).name,
                            mime="application/pdf",
                            use_container_width=True,
                            key="download_generated_resume"
                        )

    with tab2:
        st.header("📊 Job Analysis")

        if st.session_state.job_analysis:
            analysis = st.session_state.job_analysis

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Job Details")
                st.write(f"**Company:** {analysis.get('company_name', 'N/A')}")
                st.write(f"**Title:** {analysis.get('job_title', 'N/A')}")
                st.write(f"**Industry:** {analysis.get('industry', 'N/A')}")
                st.write(f"**Experience:** {analysis.get('years_of_experience', 'N/A')}")

            with col2:
                st.subheader("Education & Skills")
                st.write(f"**Education:** {analysis.get('education_requirements', 'N/A')}")

            # Keywords
            st.subheader("🔑 Key Keywords")
            keywords = analysis.get('keywords', [])
            if keywords:
                keyword_html = " ".join([f'<span style="background-color: #e1f5ff; padding: 5px 10px; margin: 3px; border-radius: 5px; display: inline-block;">{kw}</span>' for kw in keywords[:20]])
                st.markdown(keyword_html, unsafe_allow_html=True)
            else:
                st.info("No keywords extracted")

            # Skills
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Required Skills")
                required_skills = analysis.get('required_skills', [])
                if required_skills:
                    for skill in required_skills:
                        st.write(f"• {skill}")
                else:
                    st.info("No required skills listed")

            with col2:
                st.subheader("Preferred Skills")
                preferred_skills = analysis.get('preferred_skills', [])
                if preferred_skills:
                    for skill in preferred_skills:
                        st.write(f"• {skill}")
                else:
                    st.info("No preferred skills listed")

            # Responsibilities
            st.subheader("Key Responsibilities")
            responsibilities = analysis.get('key_responsibilities', [])
            if responsibilities:
                for resp in responsibilities:
                    st.write(f"• {resp}")
            else:
                st.info("No responsibilities listed")

        else:
            st.info("Generate a resume to see job analysis")

    with tab3:
        st.header("About Ultra ATS Resume Generator")

        st.markdown("""
        ### 🎯 What is this?

        The **Ultra ATS Resume Generator** is an AI-powered tool that creates highly optimized resumes designed to score 90+ in Applicant Tracking Systems (ATS).

        ### ✨ Key Features

        - **ATS Optimization**: Trained on comprehensive ATS knowledge
        - **AI-Powered**: Uses Claude (Anthropic) for intelligent generation
        - **Company Research**: Optional Perplexity integration
        - **Duplicate Detection**: Prevents regenerating same resumes
        - **Database Storage**: Keeps history of generated resumes
        - **PDF Export**: Creates ATS-friendly PDF format

        ### 🔧 How it Works

        1. **Parse Profile**: Extracts your information from Profile.pdf
        2. **Analyze Job**: Uses Claude to extract keywords and skills
        3. **Research Company**: (Optional) Gathers company insights
        4. **Generate Resume**: Creates tailored, ATS-optimized resume
        5. **Export PDF**: Generates clean, ATS-friendly PDF

        ### 📋 ATS Optimization Includes

        - ✅ Keyword optimization from job description
        - ✅ ATS-friendly formatting
        - ✅ Standard section headers
        - ✅ Achievement-focused bullet points
        - ✅ Quantifiable metrics
        - ✅ Industry-specific terminology

        ### 🔑 API Keys Required

        - **Anthropic API** (Required): For resume generation
        - **Perplexity API** (Optional): For company research

        ---

        **Integrated into AI Research Assistant** | **Powered by Claude**
        """)


if __name__ == "__main__":
    resume_maker_page()
