"""
Multi-Agent Integration
Helper module to integrate multi-agent research system with existing application
"""

import asyncio
from typing import Dict, List
from pathlib import Path

from src.multi_agent_system import MultiAgentOrchestrator
from src.comprehensive_analyzer import ComprehensiveAnalyzer
from config.settings import ENABLE_MULTI_AGENT, NUM_WORKER_AGENTS
from utils.logger import get_logger

logger = get_logger(__name__)


async def run_multi_agent_research(
    orchestrator: MultiAgentOrchestrator,
    rag_system,
    documents_data: List[Dict],
    focus_areas: List[str] = None
) -> Dict:
    """
    Run multi-agent research with comprehensive synthesis

    Args:
        orchestrator: MultiAgentOrchestrator instance
        rag_system: RAG system for context retrieval
        documents_data: Processed document data
        focus_areas: List of research focus areas

    Returns:
        Dictionary with comprehensive research results and cost info
    """
    logger.info("🚀 Starting multi-agent research...")

    # Default focus areas if none provided
    if not focus_areas:
        focus_areas = [
            "What are the main research topics and themes across all papers?",
            "What are the key methodologies and approaches used?",
            "What are the most significant findings and contributions?",
            "How do these papers relate to and build upon each other?"
        ]

    # Execute research for each focus area
    all_sections = []
    total_cost = 0.0
    cost_breakdowns = []

    for i, focus_area in enumerate(focus_areas, 1):
        logger.info(f"\n📋 Research {i}/{len(focus_areas)}: {focus_area}")

        # Run multi-agent research
        result = await orchestrator.research(
            query=focus_area,
            rag_system=rag_system,
            documents_data=documents_data
        )

        # Store section
        all_sections.append({
            'title': focus_area,
            'content': result['synthesis'],
            'sources': result['sources'],
            'images': []  # No images in multi-agent mode
        })

        # Track costs
        total_cost += result['total_cost']
        cost_breakdowns.append(result['cost_breakdown'])

        logger.info(f"✅ Research {i} complete - Cost: ${result['total_cost']:.4f}")

    # Generate executive summary
    logger.info("\n📝 Generating executive summary...")
    exec_summary = _generate_executive_summary_multi_agent(
        orchestrator,
        documents_data
    )

    # Calculate statistics
    total_pages = sum(len(d.get('pages', [])) for d in documents_data)

    return {
        'executive_summary': exec_summary,
        'detailed_sections': all_sections,
        'doc_count': len(documents_data),
        'total_pages': total_pages,
        'total_images': 0,  # No images in multi-agent mode
        'focus_areas_analyzed': len(all_sections),
        'total_cost': total_cost,
        'cost_breakdown': {
            'planning': sum(cb.get('planning', 0) for cb in cost_breakdowns),
            'execution': sum(cb.get('execution', 0) for cb in cost_breakdowns),
            'synthesis': sum(cb.get('synthesis', 0) for cb in cost_breakdowns)
        },
        'worker_count': NUM_WORKER_AGENTS,
        'total_tokens': 0  # Calculated separately if needed
    }


def _generate_executive_summary_multi_agent(
    orchestrator: MultiAgentOrchestrator,
    documents_data: List[Dict]
) -> str:
    """Generate executive summary using lead agent"""

    # Create overview of documents
    doc_overviews = []
    for doc in documents_data:
        doc_name = doc.get("doc_name", "Unknown")
        pages = doc.get("pages", [])
        page_count = len(pages)

        # Get sample text from first few pages
        sample_text = ""
        for page in pages[:3]:  # First 3 pages
            page_text = page.get("text", "")
            if page_text:
                sample_text += page_text[:1000] + "\n\n"  # First 1000 chars per page

        doc_overviews.append(
            f"**{doc_name}** ({page_count} pages)\n{sample_text}...\n"
        )

    combined_overview = "\n\n" + "=" * 80 + "\n\n".join(doc_overviews)

    # Use lead agent to create executive summary
    from src.model_router import ModelRouter

    router = ModelRouter()

    summary_prompt = f"""Based on these {len(documents_data)} research documents, create a comprehensive executive summary.

Documents Overview:
{combined_overview}

Write a detailed executive summary (4-6 paragraphs) that:

1. **Overview**: Describe the overall research area and what these papers collectively address
2. **Key Themes**: Identify the main themes and topics across all documents
3. **Major Findings**: Highlight the most significant findings and contributions
4. **Methodological Approaches**: Summarize the research methods and approaches used
5. **Connections**: Explain how these papers relate to each other
6. **Significance**: Explain why this research matters and its potential impact

Make it informative, well-structured, and engaging. Connect the dots between papers."""

    messages = [{"role": "user", "content": summary_prompt}]

    system_prompt = """You are an expert research analyst creating executive summaries.

Your task is to synthesize multiple research papers into clear, engaging executive summaries that:
- Provide high-level overview of the research area
- Identify key themes and patterns
- Highlight significant findings
- Show connections between papers
- Explain broader significance

Write in professional, flowing prose with long paragraphs (5-10 sentences) that build understanding."""

    result = router.route_task(
        task_type="synthesis",  # Use Opus for high-level synthesis
        messages=messages,
        system_prompt=system_prompt,
        max_tokens=4000,
        use_cache=True
    )

    return result["response"]


def should_use_multi_agent(model_mode: str) -> bool:
    """
    Determine if multi-agent should be used

    Args:
        model_mode: "api" or "local"

    Returns:
        True if multi-agent should be used
    """
    # Multi-agent only works with Claude API (not local models)
    if model_mode != "api":
        logger.info("ℹ️  Multi-agent requires Claude API - falling back to single-agent")
        return False

    # Check if enabled in config
    if not ENABLE_MULTI_AGENT:
        logger.info("ℹ️  Multi-agent disabled in config")
        return False

    return True


def create_comprehensive_summary_with_routing(
    model_mode: str,
    comprehensive_analyzer: ComprehensiveAnalyzer,
    multi_agent_orchestrator: MultiAgentOrchestrator,
    rag_system,
    documents_data: List[Dict],
    focus_areas: List[str] = None,
    report_mode: str = "quick"
) -> Dict:
    """
    Route to multi-agent or single-agent based on configuration

    Args:
        model_mode: "api" or "local"
        comprehensive_analyzer: Single-agent analyzer
        multi_agent_orchestrator: Multi-agent orchestrator
        rag_system: RAG system
        documents_data: Document data
        focus_areas: Optional focus areas
        report_mode: Report mode (not used in multi-agent)

    Returns:
        Summary data dictionary
    """
    # Determine which system to use
    use_multi_agent = should_use_multi_agent(model_mode)

    if use_multi_agent and multi_agent_orchestrator:
        logger.info("🚀 Using Multi-Agent Research System (Opus + Sonnet)")

        # Run multi-agent research (async)
        summary_data = asyncio.run(run_multi_agent_research(
            orchestrator=multi_agent_orchestrator,
            rag_system=rag_system,
            documents_data=documents_data,
            focus_areas=focus_areas
        ))

        return summary_data

    else:
        logger.info("⚡ Using Single-Agent Research System (Sonnet)")

        # Use existing single-agent analyzer
        summary_data = comprehensive_analyzer.create_comprehensive_summary(
            rag_system=rag_system,
            documents_data=documents_data,
            focus_areas=focus_areas,
            report_mode=report_mode
        )

        return summary_data
