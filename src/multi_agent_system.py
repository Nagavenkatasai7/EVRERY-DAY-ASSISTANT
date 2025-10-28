"""
Multi-Agent Research System
Implements Lead Agent (Opus) + Worker Agents (Sonnet) architecture for deep research
"""

import asyncio
import json
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass
import anthropic
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.model_router import ModelRouter
from src.web_search import WebSearchManager
from config.settings import ANTHROPIC_API_KEY
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ResearchSubtask:
    """Represents a research subtask for a worker agent"""
    id: int
    query: str
    focus: str
    required_depth: str  # "surface", "moderate", "deep"
    estimated_tokens: int


@dataclass
class ResearchPlan:
    """Research plan created by Lead Agent"""
    research_goal: str
    subtasks: List[ResearchSubtask]
    synthesis_strategy: str
    estimated_total_cost: float


@dataclass
class WorkerResult:
    """Result from a worker agent"""
    agent_id: int
    subtask: ResearchSubtask
    findings: str
    sources: List[Dict]
    tokens_used: int
    cost: float


class LeadAgent:
    """
    Orchestrator agent using Opus 4 for high-level planning and synthesis

    Responsibilities:
    - Analyze research queries and decompose into subtasks
    - Plan multi-agent execution strategy
    - Synthesize findings from worker agents
    - Verify quality and completeness
    """

    PLANNING_SYSTEM_PROMPT = """You are a Lead Research Agent responsible for orchestrating complex research tasks.

Your role is to:
1. Analyze research queries and understand their complexity
2. Break down complex queries into focused subtasks for worker agents
3. Plan efficient parallel execution strategies
4. Synthesize findings from multiple workers into coherent insights

You are using Claude Opus 4 for your superior planning and synthesis capabilities.

When creating research plans:
- Identify 3-5 key subtasks that together comprehensively address the query
- Each subtask should be focused, clear, and independently executable
- Consider different perspectives (theoretical, methodological, practical, comparative)
- Plan for synthesis that connects insights across subtasks

Output format:
{
    "research_goal": "Clear statement of what we're trying to learn",
    "subtasks": [
        {
            "id": 1,
            "query": "Specific focused question",
            "focus": "What aspect to emphasize",
            "required_depth": "deep|moderate|surface",
            "estimated_tokens": 8000
        }
    ],
    "synthesis_strategy": "How to combine findings"
}"""

    SYNTHESIS_SYSTEM_PROMPT = """You are a Lead Research Agent synthesizing findings from multiple worker agents.

Your role is to:
1. Combine findings from 3-5 worker agents into a unified, coherent analysis
2. Identify key themes and patterns across all findings
3. Connect insights and show relationships between different aspects
4. Create a comprehensive, flowing narrative (not bullet points)
5. Preserve source citations from worker agents

Writing style:
- Long, flowing paragraphs (5-10 sentences) that build understanding
- Connect insights from different workers seamlessly
- Professional, engaging prose
- Detailed theoretical explanations
- Proper source attribution

You are using Claude Opus 4 for your superior synthesis capabilities."""

    def __init__(self, router: ModelRouter):
        """Initialize Lead Agent with model router"""
        self.router = router
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
        logger.info("🧠 Lead Agent initialized (Claude Opus 4)")

    def plan_research(self, query: str, available_workers: int = 4) -> ResearchPlan:
        """
        Create research plan by analyzing query and decomposing into subtasks

        Args:
            query: User's research question
            available_workers: Number of worker agents available

        Returns:
            ResearchPlan with subtasks and strategy
        """
        logger.info(f"🧠 Lead Agent planning research for: {query}")

        # Build planning prompt
        planning_prompt = f"""Analyze this research query and create a detailed execution plan:

Query: "{query}"

Available worker agents: {available_workers}

Create a research plan that:
1. Breaks down the query into {min(available_workers, 5)} focused subtasks
2. Each subtask should explore a different aspect or perspective
3. Tasks should be parallelizable (independent of each other)
4. Plan for comprehensive coverage of the topic

Respond in JSON format as specified in the system prompt."""

        messages = [{"role": "user", "content": planning_prompt}]

        # Use Opus for planning (expensive but worth it for quality)
        result = self.router.route_task(
            task_type="planning",
            messages=messages,
            system_prompt=self.PLANNING_SYSTEM_PROMPT,
            max_tokens=4000,
            use_cache=True
        )

        # Parse plan
        try:
            plan_dict = json.loads(result["response"])

            subtasks = [
                ResearchSubtask(
                    id=st["id"],
                    query=st["query"],
                    focus=st["focus"],
                    required_depth=st.get("required_depth", "moderate"),
                    estimated_tokens=st.get("estimated_tokens", 8000)
                )
                for st in plan_dict["subtasks"]
            ]

            # Estimate cost
            estimated_cost = result["cost_info"]["total_cost"]
            # Add estimated worker costs (Sonnet)
            for st in subtasks:
                worker_cost_estimate = (st.estimated_tokens / 1_000_000) * 3.0  # Sonnet input pricing
                estimated_cost += worker_cost_estimate

            plan = ResearchPlan(
                research_goal=plan_dict["research_goal"],
                subtasks=subtasks,
                synthesis_strategy=plan_dict.get("synthesis_strategy", ""),
                estimated_total_cost=estimated_cost
            )

            logger.info(f"📋 Research plan created: {len(subtasks)} subtasks")
            logger.info(f"💰 Estimated total cost: ${plan.estimated_total_cost:.4f}")

            return plan

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse research plan: {str(e)}")
            # Fallback: create simple plan
            return self._create_fallback_plan(query, available_workers)

    def synthesize_findings(
        self,
        query: str,
        worker_results: List[WorkerResult],
        synthesis_strategy: str
    ) -> Dict:
        """
        Synthesize findings from all worker agents into comprehensive analysis

        Args:
            query: Original research question
            worker_results: Results from all worker agents
            synthesis_strategy: Strategy for synthesis

        Returns:
            Dictionary with synthesized analysis and metadata
        """
        logger.info(f"🧠 Lead Agent synthesizing {len(worker_results)} worker findings...")

        # Combine all worker findings
        combined_findings = []
        all_sources = []

        for i, result in enumerate(worker_results, 1):
            combined_findings.append(
                f"### Worker Agent {result.agent_id} - {result.subtask.focus}\n\n"
                f"{result.findings}\n\n"
                f"**Sources**: {len(result.sources)} documents"
            )
            all_sources.extend(result.sources)

        findings_text = "\n\n" + "="*80 + "\n\n".join(combined_findings)

        # Build synthesis prompt
        synthesis_prompt = f"""Synthesize these findings from multiple worker agents into a comprehensive analysis:

Original Query: "{query}"

Synthesis Strategy: {synthesis_strategy}

Worker Findings:
{findings_text}

Create a comprehensive, flowing narrative that:
1. Combines insights from all workers into unified analysis
2. Identifies key themes and patterns
3. Shows connections between different aspects
4. Uses long, flowing paragraphs (5-10 sentences)
5. Preserves source citations
6. Explains concepts thoroughly with theoretical depth

Write in professional, engaging prose. Make it detailed enough that someone reading it gains deep understanding of the topic."""

        messages = [{"role": "user", "content": synthesis_prompt}]

        # Use Opus for synthesis (expensive but worth it for quality)
        result = self.router.route_task(
            task_type="synthesis",
            messages=messages,
            system_prompt=self.SYNTHESIS_SYSTEM_PROMPT,
            max_tokens=8000,
            use_cache=True
        )

        # Calculate total cost
        total_cost = result["cost_info"]["total_cost"]
        for worker_result in worker_results:
            total_cost += worker_result.cost

        logger.info(f"✅ Synthesis complete")
        logger.info(f"💰 Total research cost: ${total_cost:.4f}")

        return {
            "synthesis": result["response"],
            "worker_results": worker_results,
            "sources": all_sources,
            "total_cost": total_cost,
            "cost_breakdown": {
                "planning": worker_results[0].cost if worker_results else 0,  # Placeholder
                "execution": sum(r.cost for r in worker_results),
                "synthesis": result["cost_info"]["total_cost"]
            }
        }

    def _create_fallback_plan(self, query: str, num_workers: int) -> ResearchPlan:
        """Create simple fallback plan if JSON parsing fails"""
        logger.warning("Using fallback research plan")

        subtasks = [
            ResearchSubtask(
                id=i+1,
                query=f"Analyze aspect {i+1} of: {query}",
                focus=f"Perspective {i+1}",
                required_depth="moderate",
                estimated_tokens=8000
            )
            for i in range(min(num_workers, 4))
        ]

        return ResearchPlan(
            research_goal=query,
            subtasks=subtasks,
            synthesis_strategy="Combine findings from all perspectives",
            estimated_total_cost=0.5  # Rough estimate
        )


class WorkerAgent:
    """
    Execution agent using Sonnet 4 for information gathering and analysis

    Responsibilities:
    - Execute specific research subtasks
    - Retrieve relevant context from RAG system
    - Analyze and synthesize information for assigned focus area
    - Return findings with source citations
    """

    EXECUTION_SYSTEM_PROMPT = """You are a Worker Research Agent responsible for executing focused research subtasks.

Your role is to:
1. Deeply analyze the provided context related to your assigned subtask
2. Extract key insights, findings, and theoretical explanations
3. Synthesize information into clear, flowing narrative
4. Maintain proper source citations

You are using Claude Sonnet 4 for efficient, high-quality execution.

Writing style:
- Long, flowing paragraphs (5-10 sentences)
- Detailed theoretical explanations
- Connect concepts and show relationships
- Professional, engaging prose
- Cite sources naturally

Focus on depth and clarity."""

    def __init__(self, agent_id: int = None, router: ModelRouter = None, web_search_manager: Optional[WebSearchManager] = None, worker_id: int = None, client=None):
        """
        Initialize Worker Agent

        Args:
            agent_id: Unique agent identifier (deprecated, use worker_id)
            router: Model router for API calls
            web_search_manager: Web search manager for multi-source research
            worker_id: Unique worker identifier (for test compatibility)
            client: Direct client for test compatibility
        """
        # Support both interfaces (production and test)
        self.agent_id = worker_id if worker_id is not None else agent_id
        self.worker_id = self.agent_id  # Alias for test compatibility
        self.router = router
        self.web_search_manager = web_search_manager

        # Create client if not provided
        if client:
            self.client = client
        else:
            # Create client for execute_task compatibility
            try:
                self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
            except:
                self.client = None

        logger.info(f"⚡ Worker Agent {self.agent_id} initialized (Claude Sonnet 4)")
        if web_search_manager:
            logger.debug(f"   🌐 Web search enabled for Worker {self.agent_id}")

    async def execute_subtask(
        self,
        subtask: ResearchSubtask,
        rag_system,
        documents_data: List[Dict]
    ) -> WorkerResult:
        """
        Execute research subtask with multi-source retrieval (PDF + Web)

        Args:
            subtask: Research subtask to execute
            rag_system: RAG system for context retrieval from PDFs
            documents_data: Document data for source information

        Returns:
            WorkerResult with findings and sources from both PDF and web
        """
        logger.info(f"⚡ Worker Agent {self.agent_id} executing: {subtask.focus}")

        # Step 1: Retrieve relevant context from PDFs (RAG system)
        pdf_context, pdf_metadata = rag_system.get_relevant_context(
            subtask.query,
            max_chunks=10  # Increased from 5 for better coverage
        )

        # Step 2: Retrieve relevant context from web search (if enabled)
        web_context = ""
        web_sources = []

        if self.web_search_manager and self.web_search_manager.enabled:
            try:
                logger.debug(f"   🌐 Worker {self.agent_id}: Searching web for '{subtask.query[:50]}...'")
                web_results = self.web_search_manager.search(
                    query=subtask.query,
                    max_results=5  # Limit web results per subtask
                )

                if web_results:
                    # Format web content
                    web_context_parts = []
                    for i, result in enumerate(web_results, 1):
                        web_context_parts.append(
                            f"[Web Source {i}] {result['title']}\n"
                            f"URL: {result['url']}\n"
                            f"Content: {result['content'][:1000]}..."  # Limit length
                        )
                        web_sources.append(result)

                    web_context = "\n\n".join(web_context_parts)
                    logger.info(f"   ✓ Worker {self.agent_id}: Found {len(web_results)} web sources")
                else:
                    logger.debug(f"   ℹ️  Worker {self.agent_id}: No web results found")

            except Exception as e:
                logger.warning(f"   ⚠️  Worker {self.agent_id}: Web search failed: {str(e)}")
                web_context = ""
                web_sources = []

        # Step 3: Combine contexts from both sources
        combined_context = ""
        all_sources = []

        if pdf_context:
            combined_context += "## PDF Document Sources:\n\n" + pdf_context
            all_sources.extend(pdf_metadata)

        if web_context:
            if combined_context:
                combined_context += "\n\n" + "="*80 + "\n\n"
            combined_context += "## Web Sources:\n\n" + web_context
            all_sources.extend(web_sources)

        # Check if any context was found
        if not combined_context:
            logger.warning(f"Worker Agent {self.agent_id}: No relevant context found from any source")
            return WorkerResult(
                agent_id=self.agent_id,
                subtask=subtask,
                findings="No relevant information found for this subtask from PDF or web sources.",
                sources=[],
                tokens_used=0,
                cost=0.0
            )

        # Step 4: Build execution prompt with multi-source context
        source_types = []
        if pdf_context:
            source_types.append(f"{len(pdf_metadata)} PDF documents")
        if web_sources:
            source_types.append(f"{len(web_sources)} web sources")

        source_summary = " and ".join(source_types)

        execution_prompt = f"""Execute this research subtask with deep analysis using multi-source information:

Subtask: {subtask.query}
Focus Area: {subtask.focus}
Required Depth: {subtask.required_depth}

Available Sources: {source_summary}

Retrieved Context:
{combined_context}

Analyze this content from BOTH PDF documents and web sources, then create a comprehensive response that:
1. Thoroughly addresses the subtask question
2. Explains theoretical concepts in depth
3. Uses long, flowing paragraphs (5-10 sentences)
4. Connects ideas and shows relationships across different sources
5. Includes specific details, data, and examples from the context
6. Integrates insights from both academic papers (PDFs) and current web information

Make it detailed and insightful. Explain WHY things work, not just WHAT. Synthesize information across source types when relevant."""

        messages = [{"role": "user", "content": execution_prompt}]

        # Use Sonnet for execution (5× cheaper than Opus)
        result = self.router.route_task(
            task_type="execution",
            messages=messages,
            system_prompt=self.EXECUTION_SYSTEM_PROMPT,
            max_tokens=subtask.estimated_tokens,
            use_cache=True
        )

        logger.info(
            f"✅ Worker Agent {self.agent_id} completed subtask "
            f"(PDF sources: {len(pdf_metadata)}, Web sources: {len(web_sources)})"
        )

        return WorkerResult(
            agent_id=self.agent_id,
            subtask=subtask,
            findings=result["response"],
            sources=all_sources,
            tokens_used=result["cost_info"]["input_tokens"] + result["cost_info"]["output_tokens"],
            cost=result["cost_info"]["total_cost"]
        )

    def execute_task(self, task: Dict, max_retries: int = 2) -> Dict:
        """
        Execute a task (test compatibility method)

        Args:
            task: Task dictionary with 'task' and 'context' keys
            max_retries: Maximum number of retry attempts

        Returns:
            Dictionary with 'result' key containing the task result
        """
        task_description = task.get('task', '')
        context = task.get('context', '')

        # Retry logic
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                # Use client for task execution
                if not self.client:
                    raise ValueError("Worker client not initialized")

                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2000,
                    temperature=0.7,
                    messages=[
                        {
                            "role": "user",
                            "content": f"Task: {task_description}\n\nContext: {context}\n\nPlease complete this task."
                        }
                    ]
                )
                result_text = response.content[0].text

                return {
                    'task': task_description,
                    'result': result_text,
                    'worker_id': self.worker_id
                }

            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    logger.warning(f"Worker {self.worker_id} attempt {attempt + 1} failed, retrying...")
                    continue
                else:
                    logger.error(f"Worker {self.worker_id} failed after {max_retries + 1} attempts: {str(e)}")

        # If all retries failed, return error result
        return {
            'task': task_description,
            'result': f"Task failed: {str(last_exception)}",
            'worker_id': self.worker_id,
            'error': True
        }


class MultiAgentOrchestrator:
    """
    Coordinates Lead Agent + Worker Agents for parallel research execution

    Architecture:
    - 1 Lead Agent (Opus 4): Planning + Synthesis
    - 3-4 Worker Agents (Sonnet 4): Parallel execution

    Cost optimization:
    - Expensive Opus only for planning and synthesis (2 calls)
    - Cheaper Sonnet for all execution (3-4 parallel calls)
    - Result: 40-60% cost reduction vs all-Opus architecture
    """

    def __init__(self, num_workers: int = 4, enable_web_search: bool = True):
        """
        Initialize multi-agent orchestrator with multi-source research capability

        Args:
            num_workers: Number of worker agents (default: 4 for cost optimization)
            enable_web_search: Enable web search for multi-source research (default: True)
        """
        self.router = ModelRouter()
        self.lead_agent = LeadAgent(self.router)
        self.num_workers = num_workers

        # Initialize web search manager for multi-source research
        self.web_search_manager = None
        if enable_web_search:
            try:
                self.web_search_manager = WebSearchManager()
                if self.web_search_manager.enabled:
                    logger.info("   🌐 Web search enabled (multi-source research)")
                else:
                    logger.info("   ℹ️  Web search disabled (PDF-only research)")
            except Exception as e:
                logger.warning(f"   ⚠️  Failed to initialize web search: {str(e)}")
                self.web_search_manager = None

        # Initialize worker agents with web search capability
        self.worker_agents = [
            WorkerAgent(i, self.router, self.web_search_manager)
            for i in range(1, num_workers + 1)
        ]

        # Alias for test compatibility
        self.workers = self.worker_agents
        self.lead_agent_client = self.lead_agent.client  # For test compatibility

        logger.info(f"🚀 Multi-Agent Orchestrator initialized")
        logger.info(f"   🧠 1× Lead Agent (Opus 4) - Planning & Synthesis")
        logger.info(f"   ⚡ {num_workers}× Worker Agents (Sonnet 4) - Parallel Execution")
        logger.info(f"   💰 Cost optimization: ~50% reduction vs all-Opus architecture")

    def plan_research_workflow(self, query: str, context_chunks: List[Dict]) -> Dict:
        """
        Plan research workflow based on query and available context

        Args:
            query: Research question
            context_chunks: Retrieved context chunks from RAG system

        Returns:
            Dictionary with 'subtasks' key containing list of task dictionaries
        """
        try:
            logger.info(f"📋 Planning research workflow for: {query[:100]}...")

            # Build context summary
            context_summary = ""
            if context_chunks:
                doc_names = set(chunk.get('metadata', {}).get('doc_name', 'Unknown') for chunk in context_chunks[:5])
                context_summary = f"Available context from {len(context_chunks)} chunks across {len(doc_names)} documents"

            # Use lead agent client to plan workflow
            if not self.lead_agent.client:
                logger.warning("Lead agent client not available, creating simple plan")
                return self._create_simple_plan(query, context_chunks)

            planning_prompt = f"""Analyze this research query and create a detailed execution plan:

Query: "{query}"

Context Available: {context_summary}

Create a research plan that:
1. Breaks down the query into {min(self.num_workers, 4)} focused subtasks
2. Each subtask should explore a different aspect or perspective
3. Tasks should be parallelizable (independent of each other)
4. Plan for comprehensive coverage of the topic

Respond with a JSON object containing a 'subtasks' array where each subtask has:
- "task": Clear description of what to analyze
- "context": Brief context or focus area
- "priority": 1-5 (higher is more important)

Example:
{{
  "subtasks": [
    {{"task": "Analyze methodology approaches", "context": "Focus on technical implementation", "priority": 1}},
    {{"task": "Review key findings", "context": "Focus on results and conclusions", "priority": 2}}
  ]
}}"""

            response = self.lead_agent.client.messages.create(
                model="claude-opus-4-20250514",
                max_tokens=2000,
                temperature=0.7,
                messages=[{"role": "user", "content": planning_prompt}]
            )

            # Parse response
            response_text = response.content[0].text

            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                plan_dict = json.loads(json_match.group())
                logger.info(f"✓ Created plan with {len(plan_dict.get('subtasks', []))} subtasks")
                return plan_dict
            else:
                # Fallback if JSON parsing fails
                logger.warning("Failed to parse JSON from planning response, using simple plan")
                return self._create_simple_plan(query, context_chunks)

        except Exception as e:
            logger.error(f"Error in plan_research_workflow: {str(e)}")
            return self._create_simple_plan(query, context_chunks)

    def _create_simple_plan(self, query: str, context_chunks: List[Dict]) -> Dict:
        """Create a simple fallback plan"""
        return {
            "subtasks": [
                {"task": f"Analyze: {query}", "context": "Comprehensive analysis", "priority": 1},
                {"task": f"Review findings for: {query}", "context": "Key insights", "priority": 2}
            ]
        }

    def distribute_work(self, subtasks: List[Dict]) -> List[Dict]:
        """
        Distribute work to worker agents in parallel

        Args:
            subtasks: List of task dictionaries with 'task' and 'context' keys

        Returns:
            List of result dictionaries with 'result' key
        """
        try:
            logger.info(f"⚡ Distributing {len(subtasks)} tasks to {self.num_workers} workers...")

            results = []

            # Execute tasks in parallel using ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
                # Create a mapping of future to (worker, subtask) for tracking
                future_to_task = {}

                for i, subtask in enumerate(subtasks):
                    worker_index = i % self.num_workers
                    worker = self.worker_agents[worker_index]

                    logger.debug(f"   Worker {worker.agent_id}: {subtask.get('task', '')[:50]}...")

                    # Submit task to executor for parallel execution
                    future = executor.submit(worker.execute_task, subtask)
                    future_to_task[future] = (worker, subtask)

                # Collect results as they complete
                for future in as_completed(future_to_task):
                    worker, subtask = future_to_task[future]

                    try:
                        result = future.result()
                        results.append(result)
                        logger.debug(f"   ✓ Worker {worker.agent_id} completed task")

                    except Exception as e:
                        logger.warning(f"   ✗ Worker {worker.agent_id} failed: {str(e)}")
                        # Add error result
                        results.append({
                            'task': subtask.get('task', ''),
                            'result': f"Task failed: {str(e)}",
                            'worker_id': worker.agent_id,
                            'error': True
                        })

            logger.info(f"✓ Completed {len(results)}/{len(subtasks)} tasks")
            return results

        except Exception as e:
            logger.error(f"Error in distribute_work: {str(e)}")
            return []

    def synthesize_results(self, query: str, worker_results: List[Dict]) -> str:
        """
        Synthesize worker results into final comprehensive report

        Args:
            query: Original research query
            worker_results: List of worker result dictionaries

        Returns:
            Final synthesized report as string
        """
        try:
            logger.info(f"🧠 Synthesizing {len(worker_results)} worker results...")

            # Combine worker results
            combined_findings = []
            for i, result in enumerate(worker_results, 1):
                task = result.get('task', f'Task {i}')
                finding = result.get('result', 'No result')
                worker_id = result.get('worker_id', i)

                combined_findings.append(
                    f"### Worker {worker_id} - {task}\n\n{finding}\n"
                )

            findings_text = "\n\n" + "="*80 + "\n\n".join(combined_findings)

            # Use lead agent to synthesize
            if not self.lead_agent.client:
                logger.warning("Lead agent client not available, returning combined results")
                return findings_text

            synthesis_prompt = f"""Synthesize these findings from multiple worker agents into a comprehensive analysis:

Original Query: "{query}"

Worker Findings:
{findings_text}

Create a comprehensive, flowing narrative that:
1. Combines insights from all workers into unified analysis
2. Identifies key themes and patterns
3. Shows connections between different aspects
4. Uses long, flowing paragraphs (5-10 sentences)
5. Explains concepts thoroughly with theoretical depth

Write in professional, engaging prose. Make it detailed enough that someone reading it gains deep understanding of the topic."""

            response = self.lead_agent.client.messages.create(
                model="claude-opus-4-20250514",
                max_tokens=4000,
                temperature=0.7,
                messages=[{"role": "user", "content": synthesis_prompt}]
            )

            synthesized = response.content[0].text
            logger.info(f"✓ Synthesis complete ({len(synthesized)} characters)")
            return synthesized

        except Exception as e:
            logger.error(f"Error in synthesize_results: {str(e)}")
            # Fallback: return combined findings
            return "\n\n".join(f"{r.get('task', 'Task')}: {r.get('result', 'No result')}" for r in worker_results)

    async def research(
        self,
        query: str,
        rag_system,
        documents_data: List[Dict]
    ) -> Dict:
        """
        Execute multi-agent research with parallel worker execution

        Args:
            query: Research question
            rag_system: RAG system instance
            documents_data: Processed document data

        Returns:
            Dictionary with comprehensive research results and cost information
        """
        start_time = datetime.now()
        logger.info(f"\n{'='*80}")
        logger.info(f"🚀 MULTI-AGENT RESEARCH STARTING")
        logger.info(f"Query: {query}")
        logger.info(f"{'='*80}\n")

        # Phase 1: Lead Agent creates research plan (Opus)
        logger.info("📋 Phase 1: Research Planning")
        plan = self.lead_agent.plan_research(query, available_workers=self.num_workers)

        # Show plan
        logger.info(f"\n📋 Research Plan:")
        logger.info(f"   Goal: {plan.research_goal}")
        logger.info(f"   Subtasks: {len(plan.subtasks)}")
        for subtask in plan.subtasks:
            logger.info(f"      {subtask.id}. {subtask.focus}")
        logger.info(f"   Estimated Cost: ${plan.estimated_total_cost:.4f}\n")

        # Phase 2: Worker Agents execute subtasks in parallel (Sonnet)
        logger.info(f"⚡ Phase 2: Parallel Execution ({len(plan.subtasks)} workers)")

        # Execute subtasks in parallel
        tasks = [
            worker.execute_subtask(subtask, rag_system, documents_data)
            for worker, subtask in zip(self.worker_agents[:len(plan.subtasks)], plan.subtasks)
        ]

        worker_results = await asyncio.gather(*tasks)

        # Log completion
        for result in worker_results:
            logger.info(
                f"   ✅ Worker {result.agent_id}: {result.tokens_used} tokens, "
                f"${result.cost:.4f}"
            )

        # Phase 3: Lead Agent synthesizes findings (Opus)
        logger.info(f"\n🧠 Phase 3: Synthesis")
        final_result = self.lead_agent.synthesize_findings(
            query,
            worker_results,
            plan.synthesis_strategy
        )

        # Calculate metrics
        elapsed_time = (datetime.now() - start_time).total_seconds()
        total_tokens = sum(r.tokens_used for r in worker_results)

        # Calculate source diversity (PDF vs Web)
        source_diversity = None
        if self.web_search_manager and self.web_search_manager.enabled:
            # Count PDF sources
            pdf_sources = [s for s in final_result["sources"] if s.get("source_type") != "web"]
            self.web_search_manager.update_pdf_count(len(pdf_sources))

            # Get diversity report
            source_diversity = self.web_search_manager.get_source_diversity_report()

            logger.info(f"\n📊 Source Diversity Report:")
            logger.info(f"   Total Sources: {source_diversity['total_sources']}")
            logger.info(f"   PDF Sources: {source_diversity['pdf_sources']}")
            logger.info(f"   Web Sources: {source_diversity['web_sources']}")
            logger.info(f"   Unique Web Domains: {source_diversity['unique_domains']}")
            logger.info(f"   Web Percentage: {source_diversity['web_percentage']:.1f}%")

        logger.info(f"\n{'='*80}")
        logger.info(f"✅ MULTI-AGENT RESEARCH COMPLETE")
        logger.info(f"   Time: {elapsed_time:.1f}s")
        logger.info(f"   Total Tokens: {total_tokens:,}")
        logger.info(f"   Total Cost: ${final_result['total_cost']:.4f}")
        logger.info(f"   Cost Breakdown:")
        logger.info(f"      - Planning (Opus): ${final_result['cost_breakdown'].get('planning', 0):.4f}")
        logger.info(f"      - Execution (Sonnet): ${final_result['cost_breakdown']['execution']:.4f}")
        logger.info(f"      - Synthesis (Opus): ${final_result['cost_breakdown']['synthesis']:.4f}")
        logger.info(f"{'='*80}\n")

        return {
            "query": query,
            "synthesis": final_result["synthesis"],
            "sources": final_result["sources"],
            "worker_count": len(worker_results),
            "total_cost": final_result["total_cost"],
            "cost_breakdown": final_result["cost_breakdown"],
            "elapsed_time": elapsed_time,
            "total_tokens": total_tokens,
            "research_plan": plan,
            "worker_results": worker_results,
            "source_diversity": source_diversity  # Add source diversity report
        }

    def estimate_research_cost(self, query: str, num_subtasks: int = 4) -> Dict:
        """Estimate cost before running research"""

        # Planning cost (Opus)
        planning_cost = (4000 / 1_000_000) * 15.0  # 4K tokens × $15/1M

        # Worker costs (Sonnet)
        worker_cost_each = (8000 / 1_000_000) * 3.0  # 8K tokens × $3/1M
        total_worker_cost = worker_cost_each * num_subtasks

        # Synthesis cost (Opus)
        synthesis_cost = (6000 / 1_000_000) * 15.0  # 6K tokens × $15/1M

        total_cost = planning_cost + total_worker_cost + synthesis_cost

        return {
            "estimated_total_cost": total_cost,
            "planning_cost": planning_cost,
            "execution_cost": total_worker_cost,
            "synthesis_cost": synthesis_cost,
            "num_subtasks": num_subtasks
        }
