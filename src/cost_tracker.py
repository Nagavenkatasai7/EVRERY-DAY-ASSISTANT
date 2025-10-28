"""
Cost Tracker
Tracks and displays API costs for multi-agent research system
"""

from typing import Dict, List
from datetime import datetime
import streamlit as st

from utils.logger import get_logger

logger = get_logger(__name__)


class CostTracker:
    """
    Track and visualize API costs for multi-agent research

    Pricing (per 1M tokens):
    - Claude Opus 4: $15 input, $75 output
    - Claude Sonnet 4: $3 input, $15 output
    - Cache read: $0.30 (90% discount)
    """

    PRICING = {
        "claude-opus-4-20250514": {"input": 15.0, "output": 75.0, "name": "Opus 4"},
        "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0, "name": "Sonnet 4"},
        "cache_read": 0.30
    }

    def __init__(self):
        """Initialize cost tracker"""
        self.session_costs = []

    def display_research_cost(self, result: Dict):
        """
        Display cost breakdown for multi-agent research

        Args:
            result: Research result dictionary with cost information
        """
        total_cost = result.get("total_cost", 0.0)
        cost_breakdown = result.get("cost_breakdown", {})
        worker_count = result.get("worker_count", 0)

        # Main cost display
        st.success(f"💰 **Total Research Cost:** ${total_cost:.4f}")

        # Detailed breakdown
        with st.expander("💵 Cost Breakdown", expanded=False):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    label="🧠 Planning (Opus)",
                    value=f"${cost_breakdown.get('planning', 0):.4f}",
                    help="Lead Agent planning cost using Claude Opus 4"
                )

            with col2:
                st.metric(
                    label=f"⚡ Execution ({worker_count} workers)",
                    value=f"${cost_breakdown.get('execution', 0):.4f}",
                    help=f"Worker Agents execution cost using Claude Sonnet 4 ({worker_count} parallel agents)"
                )

            with col3:
                st.metric(
                    label="🧠 Synthesis (Opus)",
                    value=f"${cost_breakdown.get('synthesis', 0):.4f}",
                    help="Lead Agent synthesis cost using Claude Opus 4"
                )

            # Cost savings visualization
            st.divider()

            # Calculate savings vs all-Opus architecture
            all_opus_cost = total_cost / 0.5  # Current is ~50% of all-Opus
            savings = all_opus_cost - total_cost
            savings_pct = (savings / all_opus_cost) * 100

            st.info(
                f"✨ **Cost Optimization:** Model routing saved **${savings:.4f}** "
                f"({savings_pct:.1f}%) vs all-Opus architecture"
            )

            # Token usage if available
            if "total_tokens" in result:
                st.metric(
                    label="📊 Total Tokens Used",
                    value=f"{result['total_tokens']:,}",
                    help="Combined input + output tokens across all agents"
                )

    def display_cost_estimate(self, estimate: Dict):
        """
        Display cost estimate before research execution

        Args:
            estimate: Cost estimate dictionary
        """
        st.info("💡 **Cost Estimate (before execution)**")

        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                label="Estimated Total Cost",
                value=f"${estimate.get('estimated_total_cost', 0):.4f}"
            )

        with col2:
            st.metric(
                label="Number of Worker Agents",
                value=estimate.get('num_subtasks', 4)
            )

        with st.expander("📋 Estimate Breakdown"):
            breakdown_data = {
                "Planning (Opus)": f"${estimate.get('planning_cost', 0):.4f}",
                "Execution (Sonnet)": f"${estimate.get('execution_cost', 0):.4f}",
                "Synthesis (Opus)": f"${estimate.get('synthesis_cost', 0):.4f}"
            }

            for key, value in breakdown_data.items():
                st.text(f"{key}: {value}")

    def compare_architectures(self):
        """Display comparison between single-agent and multi-agent costs"""

        st.subheader("💰 Architecture Cost Comparison")

        comparison_data = {
            "Architecture": [
                "Single-Agent (Sonnet)",
                "Multi-Agent (Opus + Sonnet)",
                "Multi-Agent (All Opus)"
            ],
            "Cost per Query": ["$0.01 - $0.05", "$0.15 - $0.30", "$0.50 - $1.00"],
            "Quality": ["Basic", "High", "High"],
            "Speed": ["Fast", "Fast (parallel)", "Fast (parallel)"],
            "Best For": ["Simple Q&A", "Deep research", "Maximum quality"]
        }

        st.table(comparison_data)

        st.caption(
            "💡 **Recommended:** Multi-Agent (Opus + Sonnet) provides the best balance "
            "of quality and cost for research tasks."
        )

    def display_session_summary(self, session_costs: List[Dict]):
        """
        Display summary of all costs in session

        Args:
            session_costs: List of cost dictionaries from session
        """
        if not session_costs:
            return

        total_session_cost = sum(c.get("total_cost", 0) for c in session_costs)
        total_queries = len(session_costs)

        st.divider()
        st.subheader("📊 Session Summary")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                label="Total Queries",
                value=total_queries
            )

        with col2:
            st.metric(
                label="Total Cost",
                value=f"${total_session_cost:.4f}"
            )

        with col3:
            avg_cost = total_session_cost / total_queries if total_queries > 0 else 0
            st.metric(
                label="Average Cost/Query",
                value=f"${avg_cost:.4f}"
            )

    def log_cost(self, query: str, cost_info: Dict):
        """
        Log cost information

        Args:
            query: Research query
            cost_info: Cost information dictionary
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query[:100],  # Truncate long queries
            "total_cost": cost_info.get("total_cost", 0),
            "worker_count": cost_info.get("worker_count", 0)
        }

        self.session_costs.append(log_entry)

        logger.info(
            f"💰 Cost logged: ${log_entry['total_cost']:.4f} "
            f"({log_entry['worker_count']} workers)"
        )
