# 🚀 Transformation Roadmap: Building Claude-Quality Research

## Executive Summary

Your current application is a **single-agent document Q&A system**. To match Claude's research quality, you need to transform it into a **multi-agent orchestrated research system**. This requires fundamental architectural changes, not incremental improvements.

**Current State:** Static RAG (Retrieve → Generate → Return)
**Target State:** Dynamic Multi-Agent Research (Plan → Explore → Synthesize → Verify)

**Key Metrics:**
- Current: ~5 sources, 2-5K tokens, single perspective
- Target: 50-450 sources, 30-75K tokens, multiple perspectives synthesized

---

## Critical Gaps Identified

### 🔴 **Architecture Gap (Most Critical)**

**Problem:** Single-agent, single-pass processing
**Impact:** Cannot handle complex research requiring multiple perspectives

**Current Flow:**
```
User Query → RAG System retrieves 5 chunks → Claude generates answer → Done
```

**Required Flow:**
```
User Query → Lead Agent analyzes complexity
            → Spawns 3-5 Subagents in parallel
            → Each subagent:
                - Gets own context window
                - Searches specific angle
                - Uses extended thinking
                - Makes 3-10 tool calls
            → Lead Agent synthesizes all findings
            → Citation Agent verifies claims
            → Generate comprehensive report
```

**Solution Required:** Implement orchestrator-worker pattern with LangGraph or CrewAI

---

### 🔴 **No Web Search Integration**

**Problem:** Limited to uploaded PDFs only
**Impact:** Cannot research current topics, missing 90% of available information

**Solution Required:**
1. Add Brave Search API or Tavily AI
2. Implement web scraping with asyncio
3. Combine web + local document retrieval

**Cost:** ~$5-20 per research session for 50-200 sources

---

### 🔴 **Retrieval Quality Issues**

**Problem:** Simple vector similarity, no reranking, retrieve too few chunks
**Impact:** Missing relevant information, poor answer quality

**Current:**
- Vector search only
- Retrieve 5 chunks
- No verification

**Required:**
- Hybrid search (BM25 + vector)
- Retrieve 20, rerank to 5
- Query expansion
- Cross-encoder reranking (67% failure reduction)

---

### 🟡 **Shallow Synthesis**

**Problem:** Single API call without verification
**Impact:** Surface-level answers, no cross-document insights

**Required:**
- Multi-perspective synthesis
- Claim verification
- Contradiction resolution
- Hierarchical summarization

---

### 🟡 **Low Token Investment**

**Problem:** Optimizing for cost over quality
**Impact:** Cannot do deep research

**Current:** ~2-5K tokens per query
**Required:** 30-75K tokens for complex research (15× increase)

---

## Implementation Phases

## **Phase 1: Foundation (Week 1-2) - CRITICAL**

### Goal: Upgrade core retrieval and document processing

### 1.1 Upgrade PDF Extraction

**Replace:** `src/pdf_processor.py` PyMuPDF
**With:** PyMuPDF4LLM or DocLing

```python
# Install
pip install pymupdf4llm
# OR
pip install docling

# Implementation
import pymupdf4llm

def extract_pdf_enhanced(pdf_path):
    md_text = pymupdf4llm.to_markdown(pdf_path)
    # Returns Markdown with proper table formatting
    # 20-30× faster than LlamaParse
    # Maintains document structure
    return md_text
```

**Benefits:**
- Better table extraction
- Proper structure preservation
- Faster processing (15s vs 5-7 minutes)

**Files to modify:**
- `src/pdf_processor.py:extract_text()`

---

### 1.2 Implement Hybrid Search

**Add:** BM25 keyword search + vector search

```python
# Install
pip install rank-bm25

# Implementation in src/rag_system.py
from rank_bm25 import BM25Okapi
from langchain.retrievers import EnsembleRetriever

class EnhancedRAGSystem(RAGSystem):
    def __init__(self):
        super().__init__()
        self.bm25_retriever = None

    def process_documents(self, pdf_data_list):
        # Existing vector store creation
        super().process_documents(pdf_data_list)

        # Add BM25 index
        texts = [chunk.page_content for chunk in self.documents]
        tokenized = [text.split() for text in texts]
        self.bm25_retriever = BM25Okapi(tokenized)

    def hybrid_search(self, query, k=20):
        # Vector search
        vector_results = self.vector_store.similarity_search(query, k=k)

        # BM25 search
        tokenized_query = query.split()
        bm25_scores = self.bm25_retriever.get_scores(tokenized_query)
        bm25_top_k = np.argsort(bm25_scores)[-k:]

        # Combine with weights (0.5 vector, 0.5 keyword)
        combined = self._merge_results(vector_results, bm25_top_k)
        return combined
```

**Benefits:**
- 40% better retrieval for keyword-heavy queries
- Catches exact term matches vector search misses
- Essential for academic papers with specific terminology

**Files to modify:**
- `src/rag_system.py` - Add BM25 indexing
- `requirements.txt` - Add rank-bm25

---

### 1.3 Add Reranking

**Add:** Cross-encoder reranking after retrieval

```python
# Install
pip install sentence-transformers

# Implementation
from sentence_transformers import CrossEncoder

class RerankingRAGSystem(EnhancedRAGSystem):
    def __init__(self):
        super().__init__()
        self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

    def search_with_reranking(self, query, k=5):
        # Step 1: Retrieve 20 candidates
        candidates = self.hybrid_search(query, k=20)

        # Step 2: Rerank with cross-encoder
        pairs = [[query, doc.page_content] for doc in candidates]
        scores = self.reranker.predict(pairs)

        # Step 3: Return top K
        ranked_indices = np.argsort(scores)[-k:][::-1]
        return [candidates[i] for i in ranked_indices]
```

**Benefits:**
- 67% reduction in retrieval failures (proven by Anthropic)
- Better quality in top-K results
- Catches nuanced semantic matches

**Files to modify:**
- `src/rag_system.py` - Add reranking method

---

### 1.4 Upgrade Embeddings

**Replace:** sentence-transformers/all-mpnet-base-v2
**With:** text-embedding-3-large (OpenAI) or Voyage-3

```python
# Option 1: OpenAI (best quality)
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-large",
    dimensions=3072
)

# Option 2: Voyage (best cost/performance)
from langchain_community.embeddings import VoyageEmbeddings

embeddings = VoyageEmbeddings(
    model="voyage-3.5-lite",
    voyage_api_key=VOYAGE_API_KEY
)
```

**Cost Analysis:**
- Current (free local): $0
- OpenAI large: $0.13 per 1M tokens
- Voyage lite: ~$0.08 per 1M tokens

**For 100 PDFs (10M tokens):**
- OpenAI: $1.30
- Voyage: $0.80

**Benefits:**
- 15-20% better retrieval accuracy
- Better multilingual support
- Maintained by dedicated teams

**Files to modify:**
- `config/settings.py` - Add API keys
- `src/rag_system.py` - Update embedding model

---

## **Phase 2: Multi-Agent Architecture (Week 3-4) - TRANSFORMATIONAL**

### Goal: Implement orchestrator-worker pattern

This is the **most critical change**. Without this, you cannot match Claude's quality.

### 2.1 Choose Framework

**Recommended:** LangGraph (production-grade control)
**Alternative:** CrewAI (faster prototyping)

```bash
pip install langgraph langchain-anthropic
```

### 2.2 Implement Lead Agent (Orchestrator)

**Create:** `src/orchestrator.py`

```python
import anthropic
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class ResearchPlan:
    query: str
    subtasks: List[Dict]
    estimated_agents: int
    complexity: str  # 'simple', 'moderate', 'complex'

class LeadAgent:
    """Orchestrator that plans research and spawns subagents"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.model = "claude-opus-4"  # Best for strategic planning

    def analyze_query(self, query: str) -> ResearchPlan:
        """Analyze query complexity and create research plan"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=0,
            thinking={
                "type": "enabled",
                "budget_tokens": 10000
            },
            system="""You are a research planning expert.

            Analyze the query and create a research plan:

            1. Determine complexity (simple/moderate/complex)
            2. Break into parallelizable subtasks (3-10 tasks)
            3. For each subtask specify:
               - Objective (what to find)
               - Search scope (where to look)
               - Tools needed (web search, local docs, etc)
               - Expected output format

            Output JSON:
            {
                "complexity": "moderate",
                "estimated_agents": 5,
                "subtasks": [
                    {
                        "objective": "...",
                        "scope": "...",
                        "tools": ["web_search", "local_docs"],
                        "output_format": "..."
                    }
                ]
            }""",
            messages=[{
                "role": "user",
                "content": f"Create research plan for: {query}"
            }]
        )

        # Parse JSON response
        import json
        plan_data = json.loads(response.content[0].text)

        return ResearchPlan(
            query=query,
            subtasks=plan_data['subtasks'],
            estimated_agents=plan_data['estimated_agents'],
            complexity=plan_data['complexity']
        )

    def synthesize_findings(self, subtask_results: List[str]) -> str:
        """Synthesize all subagent findings into coherent report"""

        combined = "\n\n---\n\n".join([
            f"Finding {i+1}:\n{result}"
            for i, result in enumerate(subtask_results)
        ])

        response = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            temperature=0,
            system="""You are synthesizing research findings.

            Create a comprehensive report that:
            1. Identifies common themes across findings
            2. Resolves contradictions with evidence
            3. Connects insights across sources
            4. Maintains logical narrative flow
            5. Preserves all citations

            Output structured markdown report.""",
            messages=[{
                "role": "user",
                "content": f"Synthesize these findings:\n\n{combined}"
            }]
        )

        return response.content[0].text
```

---

### 2.3 Implement Worker Agents (Subagents)

**Create:** `src/worker_agent.py`

```python
import asyncio
from typing import Dict, List

class WorkerAgent:
    """Executes specific research subtask with own context window"""

    def __init__(self, agent_id: int):
        self.agent_id = agent_id
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4"  # Cost-effective for execution
        self.findings = []

    async def execute_subtask(
        self,
        subtask: Dict,
        rag_system,
        web_search_enabled: bool = False
    ) -> str:
        """Execute research subtask with tools"""

        objective = subtask['objective']
        scope = subtask['scope']
        tools = subtask['tools']

        # Gather information from tools
        context_parts = []

        # Tool 1: Local document search
        if 'local_docs' in tools:
            local_results = rag_system.search_with_reranking(objective, k=5)
            context_parts.append(
                f"## Local Documents:\n" +
                "\n\n".join([r.page_content for r in local_results])
            )

        # Tool 2: Web search (if enabled)
        if 'web_search' in tools and web_search_enabled:
            web_results = await self.web_search(objective)
            context_parts.append(f"## Web Sources:\n{web_results}")

        combined_context = "\n\n".join(context_parts)

        # Extended thinking + analysis
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=0.3,
            thinking={
                "type": "enabled",
                "budget_tokens": 5000
            },
            system=f"""Objective: {objective}

            Analyze the gathered information and:
            1. Extract key findings relevant to objective
            2. Identify gaps in information
            3. Note contradictions or uncertainties
            4. Preserve all source citations

            Think through: What's relevant? What's missing?
            What follow-up would help?""",
            messages=[{
                "role": "user",
                "content": f"Context:\n{combined_context}\n\nAnalyze for: {objective}"
            }]
        )

        finding = response.content[0].text
        self.findings.append(finding)

        return finding

    async def web_search(self, query: str) -> str:
        """Placeholder for web search integration"""
        # Will implement in Phase 3
        return f"Web search for: {query} (to be implemented)"
```

---

### 2.4 Implement Parallel Execution

**Create:** `src/research_orchestrator.py`

```python
import asyncio
from typing import List
from src.orchestrator import LeadAgent, ResearchPlan
from src.worker_agent import WorkerAgent

class ResearchOrchestrator:
    """Coordinates multi-agent research workflow"""

    def __init__(self, rag_system):
        self.lead_agent = LeadAgent()
        self.rag_system = rag_system
        self.max_parallel_agents = 5

    async def conduct_research(self, query: str) -> Dict:
        """Full research workflow"""

        # Step 1: Plan research
        print(f"🧠 Lead Agent analyzing query...")
        plan = self.lead_agent.analyze_query(query)

        print(f"📋 Plan: {plan.complexity} research with {plan.estimated_agents} agents")

        # Step 2: Execute subagents in parallel (batch of 5)
        all_findings = []
        subtasks = plan.subtasks

        for i in range(0, len(subtasks), self.max_parallel_agents):
            batch = subtasks[i:i+self.max_parallel_agents]

            print(f"🔄 Executing agents {i+1}-{i+len(batch)}...")

            # Create worker agents for this batch
            workers = [WorkerAgent(i+j) for j in range(len(batch))]

            # Execute in parallel
            batch_findings = await asyncio.gather(*[
                worker.execute_subtask(task, self.rag_system)
                for worker, task in zip(workers, batch)
            ])

            all_findings.extend(batch_findings)

        # Step 3: Synthesize findings
        print(f"📝 Lead Agent synthesizing {len(all_findings)} findings...")
        final_report = self.lead_agent.synthesize_findings(all_findings)

        return {
            'report': final_report,
            'plan': plan,
            'findings_count': len(all_findings),
            'agents_used': len(subtasks)
        }
```

---

### 2.5 Integrate with Existing App

**Modify:** `app.py`

```python
# Add async support
import asyncio
from src.research_orchestrator import ResearchOrchestrator

# In comprehensive summary generation section:
if st.button("🔬 Generate Research Report (Multi-Agent)"):
    with st.spinner("🧠 Lead Agent planning research..."):

        # Initialize orchestrator
        orchestrator = ResearchOrchestrator(st.session_state.rag_system)

        # Run async research
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        result = loop.run_until_complete(
            orchestrator.conduct_research(user_query)
        )

        st.success(f"✅ Research complete! Used {result['agents_used']} agents")
        st.markdown(result['report'])
```

**Benefits of Multi-Agent Architecture:**
- 90% improvement in research quality (proven by Anthropic)
- Handles complex queries requiring multiple perspectives
- Parallel execution = faster completion
- Each agent has independent context window (avoids token limits)

---

## **Phase 3: Web Search Integration (Week 5-6)**

### Goal: Enable searching beyond uploaded documents

### 3.1 Choose Web Search API

**Recommended:** Brave Search API (best for RAG)

**Alternative Options:**
- Tavily AI (LLM-optimized, higher cost)
- Exa (semantic search, good for research)
- Serper (cheapest, Google results)

```bash
# Sign up at https://brave.com/search/api/
# Get API key
export BRAVE_SEARCH_API_KEY="your-key-here"
```

### 3.2 Implement Web Search Tool

**Create:** `src/web_search.py`

```python
import aiohttp
import asyncio
from typing import List, Dict

class BraveSearchTool:
    """Web search using Brave Search API"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.search.brave.com/res/v1/web/search"

    async def search(self, query: str, count: int = 10) -> List[Dict]:
        """Search web and return results"""

        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key
        }

        params = {
            "q": query,
            "count": count,
            "text_decorations": False,
            "search_lang": "en"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                self.base_url,
                headers=headers,
                params=params
            ) as response:
                data = await response.json()

        # Extract results
        results = []
        for item in data.get('web', {}).get('results', []):
            results.append({
                'title': item['title'],
                'url': item['url'],
                'description': item['description'],
                'snippet': item.get('extra_snippets', [])
            })

        return results

    async def search_and_scrape(self, query: str, count: int = 10) -> List[Dict]:
        """Search and scrape content from top results"""

        # Step 1: Search
        results = await self.search(query, count)

        # Step 2: Scrape content in parallel
        scraped_results = await self._scrape_urls([r['url'] for r in results])

        # Step 3: Combine
        for result, content in zip(results, scraped_results):
            result['content'] = content

        return results

    async def _scrape_urls(self, urls: List[str]) -> List[str]:
        """Scrape content from URLs in parallel"""

        async def scrape_single(url):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=10) as response:
                        html = await response.text()
                        # Convert HTML to markdown
                        return self._html_to_markdown(html)
            except Exception as e:
                return f"Error scraping {url}: {str(e)}"

        # Limit concurrency
        semaphore = asyncio.Semaphore(5)

        async def bounded_scrape(url):
            async with semaphore:
                return await scrape_single(url)

        return await asyncio.gather(*[bounded_scrape(url) for url in urls])

    def _html_to_markdown(self, html: str) -> str:
        """Convert HTML to clean markdown"""
        from bs4 import BeautifulSoup
        import html2text

        # Parse HTML
        soup = BeautifulSoup(html, 'html.parser')

        # Remove scripts, styles
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()

        # Convert to markdown
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        markdown = h.handle(str(soup))

        return markdown[:10000]  # Limit length
```

---

### 3.3 Integrate Web Search with Workers

**Modify:** `src/worker_agent.py`

```python
# Add web search tool
from src.web_search import BraveSearchTool

class WorkerAgent:
    def __init__(self, agent_id: int, web_search_enabled: bool = True):
        # ... existing code ...
        self.web_search_tool = BraveSearchTool(BRAVE_API_KEY) if web_search_enabled else None

    async def execute_subtask(self, subtask: Dict, rag_system) -> str:
        # ... existing code ...

        # Enhanced web search
        if 'web_search' in tools and self.web_search_tool:
            web_results = await self.web_search_tool.search_and_scrape(
                objective,
                count=10
            )

            context_parts.append(
                "## Web Sources:\n" +
                "\n\n".join([
                    f"### {r['title']}\n{r['content']}\nSource: {r['url']}"
                    for r in web_results
                ])
            )
```

---

### 3.4 Multi-Source Retrieval Strategy

**Create:** `src/multi_source_retriever.py`

```python
class MultiSourceRetriever:
    """Combines local documents + web search intelligently"""

    def __init__(self, rag_system, web_search_tool):
        self.rag_system = rag_system
        self.web_search_tool = web_search_tool

    async def retrieve(self, query: str, k: int = 10) -> List[Dict]:
        """Retrieve from multiple sources"""

        # Analyze query to determine source mix
        sources_needed = self._analyze_query_sources(query)

        results = []

        # Local documents
        if 'local' in sources_needed:
            local = self.rag_system.search_with_reranking(query, k=k)
            results.extend([{
                'content': doc.page_content,
                'source': 'local',
                'metadata': doc.metadata
            } for doc in local])

        # Web search
        if 'web' in sources_needed:
            web = await self.web_search_tool.search_and_scrape(query, count=k)
            results.extend([{
                'content': item['content'],
                'source': 'web',
                'metadata': {'url': item['url'], 'title': item['title']}
            } for item in web])

        # Deduplicate and rerank
        deduplicated = self._deduplicate(results)
        reranked = self._rerank_cross_source(query, deduplicated)

        return reranked[:k]

    def _analyze_query_sources(self, query: str) -> List[str]:
        """Determine which sources to use"""

        # Simple heuristics (can be enhanced with LLM)
        current_year = datetime.now().year

        # Check for current events indicators
        time_indicators = ['recent', 'current', 'latest', 'today', str(current_year)]
        needs_current = any(word in query.lower() for word in time_indicators)

        if needs_current:
            return ['web', 'local']  # Prioritize web for current info
        else:
            return ['local', 'web']  # Prioritize local docs

    def _deduplicate(self, results: List[Dict]) -> List[Dict]:
        """Remove duplicate content"""
        seen = set()
        unique = []

        for result in results:
            # Simple dedup by first 200 chars
            signature = result['content'][:200]
            if signature not in seen:
                seen.add(signature)
                unique.append(result)

        return unique

    def _rerank_cross_source(self, query: str, results: List[Dict]) -> List[Dict]:
        """Rerank combining sources"""
        from sentence_transformers import CrossEncoder

        reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

        pairs = [[query, r['content']] for r in results]
        scores = reranker.predict(pairs)

        # Sort by score
        ranked_indices = np.argsort(scores)[::-1]
        return [results[i] for i in ranked_indices]
```

---

## **Phase 4: Citation & Verification (Week 7)**

### Goal: Add rigorous citation tracking and claim verification

### 4.1 Implement Citation Agent

**Create:** `src/citation_agent.py`

```python
class CitationAgent:
    """Verifies claims and adds inline citations"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4"

    def add_citations(self, report: str, sources: List[Dict]) -> str:
        """Add inline citations to report"""

        # Format sources for reference
        sources_text = "\n\n".join([
            f"[{i+1}] {s.get('title', 'Untitled')}\n"
            f"Source: {s.get('source', 'Unknown')}\n"
            f"Content: {s.get('content', '')[:500]}..."
            for i, s in enumerate(sources)
        ])

        response = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            temperature=0,
            system="""You are a citation verification expert.

            Task: Add inline citations to the report.

            Instructions:
            1. For each factual claim, find supporting source
            2. Add inline citation: [Source Name, p.X]
            3. If claim has no source, mark with [VERIFY]
            4. Create bibliography at end

            Output: Report with inline citations""",
            messages=[{
                "role": "user",
                "content": f"Report:\n{report}\n\nSources:\n{sources_text}"
            }]
        )

        return response.content[0].text

    def verify_claims(self, report: str, sources: List[Dict]) -> Dict:
        """Verify all claims in report against sources"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=0,
            system="""Verify report claims against sources.

            For each major claim:
            1. Check if supported by sources
            2. Note source reference
            3. Flag if unsupported

            Output JSON:
            {
                "verified_claims": [...],
                "unsupported_claims": [...],
                "confidence_score": 0.95
            }""",
            messages=[{
                "role": "user",
                "content": f"Report:\n{report}\n\nSources:\n{sources_text}"
            }]
        )

        import json
        return json.loads(response.content[0].text)
```

---

### 4.2 Integrate Citation Agent

**Modify:** `src/research_orchestrator.py`

```python
from src.citation_agent import CitationAgent

class ResearchOrchestrator:
    def __init__(self, rag_system):
        # ... existing code ...
        self.citation_agent = CitationAgent()

    async def conduct_research(self, query: str) -> Dict:
        # ... existing steps 1-3 ...

        # Step 4: Add citations
        print(f"📎 Citation Agent verifying claims...")

        cited_report = self.citation_agent.add_citations(
            final_report,
            sources=self._collect_all_sources()
        )

        verification = self.citation_agent.verify_claims(
            cited_report,
            sources=self._collect_all_sources()
        )

        return {
            'report': cited_report,
            'verification': verification,
            'confidence': verification['confidence_score'],
            # ... existing fields ...
        }
```

---

## **Phase 5: Production Optimization (Week 8-9)**

### Goal: Performance, cost optimization, UI improvements

### 5.1 Async Processing with FastAPI Backend

**Create:** `backend/api.py`

```python
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import redis
import uuid

app = FastAPI()
redis_client = redis.Redis(host='localhost', port=6379)

class ResearchRequest(BaseModel):
    query: str
    use_web_search: bool = True
    max_sources: int = 50

class ResearchResponse(BaseModel):
    task_id: str
    status: str

@app.post("/research/start")
async def start_research(
    request: ResearchRequest,
    background_tasks: BackgroundTasks
):
    task_id = str(uuid.uuid4())

    # Start research in background
    background_tasks.add_task(
        execute_research_task,
        task_id,
        request.query,
        request.use_web_search,
        request.max_sources
    )

    return ResearchResponse(task_id=task_id, status="started")

@app.get("/research/{task_id}")
async def get_research_status(task_id: str):
    status = redis_client.get(f"task:{task_id}:status")

    if not status:
        return {"error": "Task not found"}

    status = status.decode('utf-8')

    if status == "completed":
        result = redis_client.get(f"task:{task_id}:result")
        return {
            "status": "completed",
            "result": json.loads(result)
        }
    elif status == "running":
        progress = redis_client.get(f"task:{task_id}:progress")
        return {
            "status": "running",
            "progress": progress.decode('utf-8') if progress else "0%"
        }

    return {"status": status}

async def execute_research_task(
    task_id: str,
    query: str,
    use_web_search: bool,
    max_sources: int
):
    try:
        redis_client.set(f"task:{task_id}:status", "running")

        # Initialize orchestrator
        orchestrator = ResearchOrchestrator(rag_system)

        # Execute research
        result = await orchestrator.conduct_research(query)

        # Store result
        redis_client.set(
            f"task:{task_id}:result",
            json.dumps(result),
            ex=3600  # Expire after 1 hour
        )
        redis_client.set(f"task:{task_id}:status", "completed")

    except Exception as e:
        redis_client.set(f"task:{task_id}:status", "failed")
        redis_client.set(f"task:{task_id}:error", str(e))
```

---

### 5.2 Enhanced UI

**Modify:** `app.py` for better UX

```python
import streamlit as st
import asyncio
import time

st.title("🔬 AI Research Assistant (Multi-Agent)")

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Research Configuration")

    research_mode = st.radio(
        "Research Mode",
        ["Simple Q&A", "Multi-Agent Research"],
        help="Simple Q&A uses single agent, Multi-Agent uses 3-10 agents in parallel"
    )

    enable_web_search = st.checkbox(
        "Enable Web Search",
        value=True,
        help="Search beyond uploaded documents"
    )

    max_agents = st.slider(
        "Max Parallel Agents",
        min_value=3,
        max_value=10,
        value=5,
        help="More agents = better quality but higher cost"
    )

# Main interface
query = st.text_area(
    "Research Query",
    placeholder="Example: Compare the methodologies used in recent quantum computing papers...",
    height=100
)

if st.button("🔬 Start Research"):

    if research_mode == "Multi-Agent Research":
        # Multi-agent research
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Show planning phase
        status_text.text("🧠 Lead Agent analyzing query...")
        progress_bar.progress(10)

        # Initialize orchestrator
        orchestrator = ResearchOrchestrator(st.session_state.rag_system)

        # Create async loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Execute with progress updates
        status_text.text("📋 Creating research plan...")
        progress_bar.progress(20)

        result = loop.run_until_complete(
            orchestrator.conduct_research(query)
        )

        progress_bar.progress(100)
        status_text.text("✅ Research complete!")

        # Display results
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Agents Used", result['agents_used'])
        with col2:
            st.metric("Sources Analyzed", result['findings_count'])
        with col3:
            st.metric("Confidence", f"{result['confidence']:.1%}")

        # Display report
        st.markdown("## 📄 Research Report")
        st.markdown(result['report'])

        # Download options
        st.download_button(
            "📥 Download Markdown",
            result['report'],
            file_name=f"research_{int(time.time())}.md",
            mime="text/markdown"
        )

    else:
        # Simple Q&A mode (existing implementation)
        st.write("Using simple Q&A mode...")
```

---

### 5.3 Cost Optimization

**Implement intelligent routing:**

```python
class CostOptimizedOrchestrator(ResearchOrchestrator):
    """Routes queries based on complexity to optimize cost"""

    def __init__(self, rag_system):
        super().__init__(rag_system)
        self.cost_tracker = {}

    async def conduct_research(self, query: str) -> Dict:
        # Analyze query complexity with cheap model first
        complexity = await self._quick_complexity_check(query)

        if complexity == 'simple':
            # Use single agent for simple queries
            return await self._simple_research(query)
        else:
            # Use multi-agent for complex queries
            return await super().conduct_research(query)

    async def _quick_complexity_check(self, query: str) -> str:
        """Quick complexity check using Sonnet (cheaper)"""

        response = self.client.messages.create(
            model="claude-sonnet-4",
            max_tokens=100,
            temperature=0,
            system="Classify query complexity: simple/complex. "
                   "Simple = single fact. Complex = requires synthesis.",
            messages=[{"role": "user", "content": query}]
        )

        return response.content[0].text.lower().strip()
```

---

## **Phase 6: Advanced Features (Week 10+)**

### Optional enhancements for production system:

### 6.1 Extended Thinking Integration

```python
# In Lead Agent planning
response = self.client.messages.create(
    model=self.model,
    max_tokens=4096,
    thinking={
        "type": "enabled",
        "budget_tokens": 10000  # Allow deep thinking
    },
    # ... rest of config
)
```

### 6.2 Memory & Session Persistence

```python
class ResearchMemory:
    """Persist research context across sessions"""

    def __init__(self):
        self.memory_store = {}

    def save_context(self, session_id: str, context: Dict):
        """Save research context"""
        self.memory_store[session_id] = {
            'findings': context['findings'],
            'sources': context['sources'],
            'timestamp': datetime.now()
        }

    def load_context(self, session_id: str) -> Dict:
        """Load previous research context"""
        return self.memory_store.get(session_id, {})
```

### 6.3 Human-in-the-Loop

```python
class InteractiveOrchestrator(ResearchOrchestrator):
    """Allow human guidance during research"""

    async def conduct_research_interactive(self, query: str):
        # ... execute research ...

        # Pause for human feedback
        feedback = await self.request_human_feedback(
            "Research plan created. Approve?"
        )

        if feedback == 'modify':
            # Adjust plan based on human input
            pass
```

---

## Summary: Critical Path to Claude Quality

### **Must-Have Changes (Phases 1-3):**

1. ✅ **Multi-Agent Architecture** - Without this, you cannot match Claude's quality
2. ✅ **Hybrid Search + Reranking** - Essential for retrieval quality
3. ✅ **Web Search Integration** - Required for true research (not just document Q&A)
4. ✅ **Parallel Execution** - Enables breadth-first exploration

### **Important Improvements (Phase 4-5):**

5. ✅ **Citation Verification** - Builds trust and accuracy
6. ✅ **Async Backend** - Production-grade performance
7. ✅ **Cost Optimization** - Intelligent routing

### **Nice-to-Have (Phase 6):**

8. Extended thinking
9. Session memory
10. Human-in-the-loop

---

## Expected Outcomes

**After Phase 1-2 (Weeks 1-4):**
- 3-5× better retrieval quality
- Multi-agent architecture working
- Can handle complex research queries

**After Phase 3 (Week 6):**
- Can search 50-200 sources beyond uploaded PDFs
- True research capability (not just Q&A)

**After Phase 4-5 (Week 9):**
- Production-ready system
- Rigorous citations
- Optimized costs

---

## Cost Implications

**Current System:**
- ~$0.10-0.30 per query
- 2-5K tokens per query

**Target System:**
- ~$0.50-5.00 per query depending on complexity
- 30-75K tokens for complex research
- **But:** Research quality justifies 10-20× cost increase
- **ROI:** Compare to human researcher time (hours × hourly rate)

**Optimization:**
- Use Sonnet for workers (40-60% cost reduction vs Opus)
- Intelligent routing (simple queries stay cheap)
- Caching enabled (already done)

---

## Implementation Priority

### Week 1-2: **Foundation** ⭐⭐⭐⭐⭐
- Hybrid search
- Reranking
- Better PDF extraction
- Upgrade embeddings

### Week 3-4: **Multi-Agent** ⭐⭐⭐⭐⭐
- Lead Agent (orchestrator)
- Worker Agents (subagents)
- Parallel execution
- Synthesis logic

### Week 5-6: **Web Search** ⭐⭐⭐⭐
- Brave/Tavily API integration
- Web scraping
- Multi-source retrieval

### Week 7: **Citations** ⭐⭐⭐⭐
- Citation Agent
- Verification logic

### Week 8-9: **Production** ⭐⭐⭐
- FastAPI backend
- Async processing
- Better UI

---

## Next Steps

1. **Decision Point:** Commit to multi-agent architecture? (This is the key transformation)
2. **Choose Framework:** LangGraph (recommended) or CrewAI
3. **Start Phase 1:** Upgrade retrieval quality (can be done in parallel with planning Phase 2)
4. **Allocate Budget:** Expect 10-20× increase in API costs for quality improvement

**Questions to Answer:**
- Are you willing to invest 10-20× more in API costs for research quality?
- Do you want to focus on PhD research (deep, thorough) or general Q&A (fast, cheap)?
- Timeline: 4 weeks minimum for transformation, 9 weeks for full production system

---

This roadmap transforms your application from a **document Q&A tool** into a **research-grade synthesis system** matching Claude's quality level. The key insight: **architecture matters more than individual component improvements**.
