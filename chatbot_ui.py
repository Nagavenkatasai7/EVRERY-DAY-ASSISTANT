"""
Chatbot UI Components
Add these functions to app.py to enable the chatbot feature
"""

import streamlit as st
from src.document_session import SessionManager
from src.chatbot import DocumentChatbot
from utils.logger import get_logger

logger = get_logger(__name__)


def display_chatbot_tab():
    """Display the chatbot interface tab"""
    st.header("💬 Chat with Your Documents")

    # Load available sessions
    sessions = SessionManager.list_sessions()

    if not sessions:
        st.info("""
        📝 **No document sessions available yet!**

        Please process some documents in the "Process Documents" tab first.
        Once processed, your document session will appear here for Q&A.
        """)
        return

    # Session selector
    st.subheader("📚 Select Document Session")

    session_options = {
        f"{s['session_name']} ({s['source_pdf_count']} docs, {s['total_pages']} pages)": s['session_id']
        for s in sessions
    }

    selected_session_display = st.selectbox(
        "Choose a session to chat with:",
        options=list(session_options.keys()),
        help="Select which set of documents you want to ask questions about"
    )

    selected_session_id = session_options[selected_session_display]

    # Load session
    session = SessionManager.get_session(selected_session_id)
    if not session:
        st.error("Failed to load session")
        return

    # Display session info
    with st.expander("ℹ️ Session Details", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Source PDFs", session.metadata["source_pdf_count"])
        with col2:
            st.metric("Total Pages", session.metadata.get("total_pages", 0))
        with col3:
            st.metric("Total Images", session.metadata.get("total_images", 0))

        st.write("**Source Documents:**")
        for pdf_name in session.metadata.get("source_pdf_names", []):
            st.write(f"- {pdf_name}")

        # Show summary PDF status
        st.write("")  # Spacing
        if session.metadata.get("has_summary"):
            summary_pdf_name = session.metadata.get("summary_pdf_name", "")
            st.write("**Generated Summary:**")
            st.write(f"- ✅ {summary_pdf_name}")

            # Check if summary is in RAG system
            try:
                # Load RAG to check if summary chunks exist
                from src.rag_system import RAGSystem
                temp_rag = RAGSystem()
                session.load_rag_system(temp_rag)

                # Count chunks from summary PDF
                summary_chunks = [
                    chunk for chunk in temp_rag.chunks_metadata
                    if summary_pdf_name in chunk.get("doc_name", "")
                ]

                if summary_chunks:
                    st.write(f"- 🟢 **RAG Status**: In RAG system ({len(summary_chunks)} chunks)")
                else:
                    st.write(f"- 🟡 **RAG Status**: Not in RAG (click 'Fix Session' below)")
            except Exception as e:
                st.write(f"- ⚠️ **RAG Status**: Unable to check")
        else:
            st.write("**Generated Summary:**")
            st.write("- ❌ No summary generated for this session")

    # Session Regeneration Tool (for old sessions missing summary PDF in RAG)
    if session.metadata.get("has_summary"):
        with st.expander("🔧 Fix Old Session (Add Summary to RAG)", expanded=False):
            st.write("""
            **Is your chatbot reading from source PDFs instead of the summary?**

            If this session was created before the bug fix, the generated summary PDF might not be
            included in the RAG system. Click the button below to fix it.

            This will:
            - Check if the summary PDF is already in RAG
            - If not, add it automatically (keeps all source PDFs too)
            - Re-save the session
            """)

            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("🔄 Fix Session", type="secondary", key="regenerate_rag_btn"):
                    with st.spinner("Fixing session..."):
                        success = regenerate_session_rag(selected_session_id)

                    if success:
                        st.balloons()
                        st.rerun()

    st.divider()

    # Initialize chatbot
    if 'current_chatbot_session' not in st.session_state or st.session_state.current_chatbot_session != selected_session_id:
        st.session_state.current_chatbot_session = selected_session_id
        st.session_state.chat_messages = []

        # Create chatbot
        model_mode = st.session_state.get('model_mode', 'api')
        selected_local_model = st.session_state.get('selected_local_model', None)

        try:
            st.session_state.chatbot = DocumentChatbot(
                session=session,
                model_mode=model_mode,
                local_model_name=selected_local_model if model_mode == "local" else None
            )
            logger.info(f"Initialized chatbot for session: {selected_session_id}")
        except Exception as e:
            st.error(f"❌ Failed to initialize chatbot: {str(e)}")
            logger.error(f"Chatbot initialization error: {str(e)}")
            return

    # Chat interface
    st.subheader("💭 Ask Questions")

    # Display chat history
    for message in st.session_state.chat_messages:
        with st.chat_message("user"):
            st.write(message["question"])

        with st.chat_message("assistant"):
            st.write(message["answer"])

            # Show search stage indicator
            search_stage = message.get("search_stage", "unknown")
            if search_stage == "summary":
                st.caption("🔍 Answer from: Summary PDF")
            elif search_stage == "sources":
                st.caption("🔍 Answer from: Summary PDF + Source PDFs")

            if message.get("sources"):
                with st.expander(f"📚 Sources ({len(message['sources'])} references)", expanded=False):
                    for i, source in enumerate(message["sources"], 1):
                        st.write(f"**{i}.** {source['source']} - {source['section']}")

    # Chat input
    question = st.chat_input("Ask a question about your documents...")

    if question:
        # Add user message
        with st.chat_message("user"):
            st.write(question)

        # Get answer from chatbot
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    result = st.session_state.chatbot.ask_question(question)

                    if result["context_found"]:
                        st.write(result["answer"])

                        # Show search stage indicator
                        search_stage = result.get("search_stage", "unknown")
                        if search_stage == "summary":
                            st.caption("🔍 Answer from: Summary PDF")
                        elif search_stage == "sources":
                            st.caption("🔍 Answer from: Summary PDF + Source PDFs")

                        if result["sources"]:
                            with st.expander(f"📚 Sources ({len(result['sources'])} references)", expanded=False):
                                for i, source in enumerate(result["sources"], 1):
                                    st.write(f"**{i}.** {source['source']} - {source['section']}")
                    else:
                        st.write(result["answer"])

                    # Store in chat history
                    st.session_state.chat_messages.append({
                        "question": question,
                        "answer": result["answer"],
                        "sources": result.get("sources", []),
                        "search_stage": result.get("search_stage", "unknown")
                    })

                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    logger.error(f"Chatbot error: {str(e)}")

    # Clear chat button
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_messages = []
            if hasattr(st.session_state, 'chatbot'):
                st.session_state.chatbot.clear_history()
            st.rerun()


def regenerate_session_rag(session_id: str) -> bool:
    """
    Regenerate a session's RAG system by adding the saved summary PDF
    This fixes old sessions that were created before the summary PDF bug fix

    Args:
        session_id: ID of the session to regenerate

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Starting RAG regeneration for session: {session_id}")

        # Load the session
        session = SessionManager.get_session(session_id)
        if not session:
            st.error("❌ Failed to load session")
            return False

        # Check if session has a summary PDF
        if not session.metadata.get("has_summary"):
            st.warning("⚠️ This session doesn't have a summary PDF to add")
            return False

        # Get summary PDF path from session
        summary_pdf_name = session.metadata.get("summary_pdf_name", "")
        if not summary_pdf_name:
            st.error("❌ Session metadata missing summary PDF name")
            return False

        # Find the summary PDF file (using session.summary_dir property)
        summary_pdf_path = session.summary_dir / summary_pdf_name
        if not summary_pdf_path.exists():
            st.error(f"❌ Summary PDF file not found: {summary_pdf_name}")
            st.info("The summary PDF file may have been deleted or moved.")
            return False

        # Initialize RAG system
        from src.rag_system import RAGSystem
        rag_system = RAGSystem()

        # Load existing RAG store
        try:
            session.load_rag_system(rag_system)
            logger.info(f"Loaded existing RAG with {len(rag_system.chunks_metadata)} chunks")
        except Exception as e:
            st.error(f"❌ Failed to load existing RAG system: {str(e)}")
            return False

        # Check if summary PDF is already in RAG
        summary_chunks = [
            chunk for chunk in rag_system.chunks_metadata
            if summary_pdf_name in chunk.get("doc_name", "")
        ]

        if summary_chunks:
            st.info(f"ℹ️ Summary PDF is already in RAG system ({len(summary_chunks)} chunks)")
            return True

        # Process the summary PDF
        from src.pdf_processor import process_multiple_pdfs
        logger.info(f"Processing summary PDF: {summary_pdf_name}")

        with st.spinner("Processing summary PDF..."):
            summary_pdf_data = process_multiple_pdfs([summary_pdf_path])

        if not summary_pdf_data:
            st.error("❌ Failed to process summary PDF")
            return False

        # Add summary to RAG system
        chunks_before = len(rag_system.chunks_metadata)
        logger.info(f"Adding summary PDF to RAG (current chunks: {chunks_before})")

        with st.spinner("Adding summary to RAG system..."):
            new_chunks = rag_system.add_documents(summary_pdf_data)

        chunks_after = len(rag_system.chunks_metadata)
        logger.info(f"✓ Added {new_chunks} chunks (total: {chunks_before} → {chunks_after})")

        # Re-save the session with updated RAG
        with st.spinner("Saving updated session..."):
            session.store_rag_system(rag_system)

        st.success(f"✅ Successfully added summary PDF to session! ({new_chunks} new chunks)")
        logger.info(f"Session RAG regeneration complete for {session_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to regenerate session RAG: {str(e)}")
        st.error(f"❌ Regeneration failed: {str(e)}")
        return False


def save_session_after_processing(pdf_paths, summary_pdf_path, session_name=None):
    """
    Save processed documents to a session

    Args:
        pdf_paths: List of source PDF paths
        summary_pdf_path: Path to generated summary PDF
        session_name: Optional custom session name

    Returns:
        DocumentSession instance
    """
    try:
        # Create new session
        if not session_name:
            session_name = f"Research Session - {len(pdf_paths)} documents"

        session = SessionManager.create_session(session_name)
        logger.info(f"Created new session: {session.session_id}")

        # Store source PDFs
        session.store_source_pdfs(pdf_paths)

        # Store summary PDF file
        session.store_summary_pdf(summary_pdf_path)

        # CRITICAL FIX: Add summary PDF to RAG system before saving
        # This ensures the chatbot can search the generated summary
        if st.session_state.rag_system and summary_pdf_path and summary_pdf_path.exists():
            try:
                from src.pdf_processor import process_multiple_pdfs
                logger.info(f"Processing summary PDF for RAG system: {summary_pdf_path.name}")

                # Process the summary PDF
                summary_pdf_data = process_multiple_pdfs([summary_pdf_path])

                if summary_pdf_data:
                    # Get current chunk count before adding summary
                    chunks_before = len(st.session_state.rag_system.chunks_metadata)

                    # Add summary PDF chunks to existing RAG system (APPEND, not replace!)
                    # This uses the new add_documents() method which preserves existing chunks
                    new_chunks = st.session_state.rag_system.add_documents(summary_pdf_data)

                    chunks_after = len(st.session_state.rag_system.chunks_metadata)
                    logger.info(f"✓ Added summary PDF to RAG: {new_chunks} new chunks (total: {chunks_before} → {chunks_after})")
                else:
                    logger.warning("Summary PDF processing returned no data")

            except Exception as e:
                # Don't fail the entire session save if summary processing fails
                # Just log and continue with source PDFs only
                logger.error(f"Failed to process summary PDF for RAG: {str(e)}")
                logger.warning("Session will be saved with source PDFs only (summary PDF file saved but not in RAG)")

        # Store RAG system (now includes both source PDFs AND summary PDF)
        if st.session_state.rag_system:
            session.store_rag_system(st.session_state.rag_system)

        # Update statistics
        if st.session_state.analysis_results:
            session.update_statistics(
                total_pages=st.session_state.analysis_results.get('total_pages', 0),
                total_images=st.session_state.analysis_results.get('total_images', 0)
            )

        logger.info(f"Session saved successfully: {session.session_id}")
        return session

    except Exception as e:
        logger.error(f"Failed to save session: {str(e)}")
        st.warning(f"⚠️ Session save failed: {str(e)}")
        return None


# ADD TO initialize_session_state():
def add_to_session_state():
    """Add these to your initialize_session_state() function"""
    if 'current_chatbot_session' not in st.session_state:
        st.session_state.current_chatbot_session = None
    if 'chatbot' not in st.session_state:
        st.session_state.chatbot = None
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []


# MODIFIED MAIN FUNCTION with tabs
def main_with_tabs():
    """
    REPLACE your current main() function with this
    """
    try:
        # Initialize
        initialize_session_state()

        # Display UI
        display_header()
        display_sidebar()

        # Main content with tabs
        tab1, tab2 = st.tabs(["📄 Process Documents", "💬 Chat with Documents"])

        with tab1:
            # Original workflow
            file_paths = upload_documents()

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

                # Generate report and save session
                summary_pdf_path = generate_report()

                if summary_pdf_path:
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
        logger.error(f"Application error: {str(e)}")

        if st.button("🔄 Restart Application"):
            reset_session()
            st.rerun()
