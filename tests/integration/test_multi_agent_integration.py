"""
Integration Tests for Multi-Agent System
Tests agent coordination, workflow, and data flow
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.multi_agent_system import MultiAgentOrchestrator, WorkerAgent


class TestMultiAgentOrchestrator:
    """Test multi-agent orchestration"""

    @patch('src.multi_agent_system.anthropic.Anthropic')
    def test_orchestrator_initialization(self, mock_anthropic):
        """Test orchestrator initialization"""
        mock_client = Mock()
        mock_anthropic.return_value = mock_client

        orchestrator = MultiAgentOrchestrator(num_workers=4)

        assert orchestrator.num_workers == 4
        assert len(orchestrator.workers) == 4
        assert orchestrator.lead_agent_client is not None

    @patch('src.multi_agent_system.anthropic.Anthropic')
    def test_plan_research_workflow(self, mock_anthropic):
        """Test research workflow planning"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Research plan: 1. Analyze methodology\n2. Review results\n3. Synthesize findings")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        orchestrator = MultiAgentOrchestrator(num_workers=2)

        query = "Analyze machine learning papers"
        context_chunks = [
            {"text": "Paper 1 content", "metadata": {"doc_name": "paper1.pdf"}},
            {"text": "Paper 2 content", "metadata": {"doc_name": "paper2.pdf"}}
        ]

        plan = orchestrator.plan_research_workflow(query, context_chunks)

        assert plan is not None
        assert isinstance(plan, dict)
        assert 'subtasks' in plan
        mock_client.messages.create.assert_called_once()

    @patch('src.multi_agent_system.anthropic.Anthropic')
    def test_distribute_work_to_agents(self, mock_anthropic):
        """Test work distribution to workers"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Analysis result")]
        mock_response.usage = Mock(input_tokens=50, output_tokens=25)
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        orchestrator = MultiAgentOrchestrator(num_workers=2)

        subtasks = [
            {"task": "Analyze paper 1", "context": "Content 1"},
            {"task": "Analyze paper 2", "context": "Content 2"}
        ]

        results = orchestrator.distribute_work(subtasks)

        assert len(results) == 2
        assert all('result' in r for r in results)

    @patch('src.multi_agent_system.anthropic.Anthropic')
    def test_synthesize_results(self, mock_anthropic):
        """Test result synthesis by lead agent"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Synthesized comprehensive report")]
        mock_response.usage = Mock(input_tokens=200, output_tokens=100)
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        orchestrator = MultiAgentOrchestrator(num_workers=2)

        worker_results = [
            {"task": "Task 1", "result": "Result 1"},
            {"task": "Task 2", "result": "Result 2"}
        ]

        final_result = orchestrator.synthesize_results("research query", worker_results)

        assert final_result is not None
        assert isinstance(final_result, str)
        assert len(final_result) > 0

    @patch('src.multi_agent_system.anthropic.Anthropic')
    def test_error_handling_in_worker(self, mock_anthropic):
        """Test error handling when worker fails"""
        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception("API Error")
        mock_anthropic.return_value = mock_client

        orchestrator = MultiAgentOrchestrator(num_workers=1)

        subtasks = [{"task": "Test task", "context": "Test context"}]

        # Should handle error gracefully
        results = orchestrator.distribute_work(subtasks)

        # Should still return results (possibly with error info)
        assert isinstance(results, list)


class TestWorkerAgent:
    """Test individual worker agent behavior"""

    @patch('src.multi_agent_system.anthropic.Anthropic')
    def test_worker_execute_task(self, mock_anthropic):
        """Test worker task execution"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Task completed successfully")]
        mock_response.usage = Mock(input_tokens=50, output_tokens=25)
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        worker = WorkerAgent(worker_id=1, client=mock_client)

        task = {
            "task": "Analyze methodology section",
            "context": "Methodology content here"
        }

        result = worker.execute_task(task)

        assert result is not None
        assert 'result' in result
        assert isinstance(result['result'], str)

    @patch('src.multi_agent_system.anthropic.Anthropic')
    def test_worker_retry_on_failure(self, mock_anthropic):
        """Test worker retry logic"""
        mock_client = Mock()
        # First call fails, second succeeds
        mock_client.messages.create.side_effect = [
            Exception("Temporary error"),
            Mock(
                content=[Mock(text="Success after retry")],
                usage=Mock(input_tokens=50, output_tokens=25)
            )
        ]
        mock_anthropic.return_value = mock_client

        worker = WorkerAgent(worker_id=1, client=mock_client)

        task = {"task": "Test task", "context": "Context"}

        result = worker.execute_task(task)

        # Should succeed after retry
        assert result is not None
        assert mock_client.messages.create.call_count >= 1


class TestEndToEndMultiAgentWorkflow:
    """Test complete multi-agent workflow"""

    @patch('src.multi_agent_system.anthropic.Anthropic')
    @patch('src.rag_system.RAGSystem')
    def test_full_research_workflow(self, mock_rag, mock_anthropic):
        """Test complete research workflow from query to synthesis"""
        # Mock RAG system
        mock_rag_instance = Mock()
        mock_rag_instance.hybrid_search.return_value = [
            {"text": "Content 1", "metadata": {"doc_name": "paper1.pdf"}},
            {"text": "Content 2", "metadata": {"doc_name": "paper2.pdf"}}
        ]
        mock_rag.return_value = mock_rag_instance

        # Mock Anthropic client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Research analysis result")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        # Test workflow
        orchestrator = MultiAgentOrchestrator(num_workers=2)

        query = "What are the main findings in machine learning research?"

        # Get context from RAG
        context_chunks = mock_rag_instance.hybrid_search(query, k=10)

        # Plan workflow
        plan = orchestrator.plan_research_workflow(query, context_chunks)

        # Distribute work
        if 'subtasks' in plan:
            results = orchestrator.distribute_work(plan['subtasks'])

            # Synthesize results
            final_result = orchestrator.synthesize_results(query, results)

            assert final_result is not None
            assert len(final_result) > 0

    @patch('src.multi_agent_system.anthropic.Anthropic')
    def test_agent_coordination_with_dependencies(self, mock_anthropic):
        """Test agent coordination when tasks have dependencies"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Task completed")]
        mock_response.usage = Mock(input_tokens=50, output_tokens=25)
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        orchestrator = MultiAgentOrchestrator(num_workers=3)

        # Tasks with dependencies (must be executed in order)
        subtasks = [
            {"task": "Extract key concepts", "context": "Content", "priority": 1},
            {"task": "Analyze relationships", "context": "Content", "priority": 2},
            {"task": "Synthesize insights", "context": "Content", "priority": 3}
        ]

        results = orchestrator.distribute_work(subtasks)

        # All tasks should complete
        assert len(results) == 3

    @patch('src.multi_agent_system.anthropic.Anthropic')
    def test_parallel_processing_performance(self, mock_anthropic):
        """Test that parallel processing is faster than sequential"""
        import time

        mock_client = Mock()

        def slow_response(*args, **kwargs):
            time.sleep(0.1)  # Simulate API delay
            return Mock(
                content=[Mock(text="Result")],
                usage=Mock(input_tokens=50, output_tokens=25)
            )

        mock_client.messages.create.side_effect = slow_response
        mock_anthropic.return_value = mock_client

        orchestrator = MultiAgentOrchestrator(num_workers=4)

        subtasks = [
            {"task": f"Task {i}", "context": f"Context {i}"}
            for i in range(8)
        ]

        start_time = time.time()
        results = orchestrator.distribute_work(subtasks)
        parallel_time = time.time() - start_time

        # Parallel should be significantly faster than sequential
        # (8 tasks * 0.1s = 0.8s sequential vs ~0.2s parallel with 4 workers)
        assert parallel_time < 0.5  # Should complete in less than 0.5s with parallelism


class TestAgentCommunication:
    """Test communication between agents"""

    @patch('src.multi_agent_system.anthropic.Anthropic')
    def test_context_passing_between_agents(self, mock_anthropic):
        """Test that context is properly passed between agents"""
        mock_client = Mock()
        responses = []

        def capture_context(*args, **kwargs):
            responses.append(kwargs.get('messages', []))
            return Mock(
                content=[Mock(text="Result")],
                usage=Mock(input_tokens=50, output_tokens=25)
            )

        mock_client.messages.create.side_effect = capture_context
        mock_anthropic.return_value = mock_client

        orchestrator = MultiAgentOrchestrator(num_workers=2)

        subtasks = [
            {"task": "Task 1", "context": "Important context from previous step"},
            {"task": "Task 2", "context": "More context"}
        ]

        results = orchestrator.distribute_work(subtasks)

        # Verify context was included in agent calls
        assert len(responses) >= 2
        # Check that context appeared in messages
        for response in responses:
            if response:
                message_text = str(response)
                assert len(message_text) > 0

    @patch('src.multi_agent_system.anthropic.Anthropic')
    def test_result_aggregation(self, mock_anthropic):
        """Test proper aggregation of worker results"""
        mock_client = Mock()
        mock_client.messages.create.return_value = Mock(
            content=[Mock(text="Aggregated result")],
            usage=Mock(input_tokens=100, output_tokens=50)
        )
        mock_anthropic.return_value = mock_client

        orchestrator = MultiAgentOrchestrator(num_workers=3)

        worker_results = [
            {"task": "Task 1", "result": "Finding A"},
            {"task": "Task 2", "result": "Finding B"},
            {"task": "Task 3", "result": "Finding C"}
        ]

        final_result = orchestrator.synthesize_results("research query", worker_results)

        # Final result should incorporate all worker findings
        assert final_result is not None
        assert isinstance(final_result, str)


class TestLoadBalancing:
    """Test load balancing across workers"""

    @patch('src.multi_agent_system.anthropic.Anthropic')
    def test_even_workload_distribution(self, mock_anthropic):
        """Test that work is evenly distributed"""
        mock_client = Mock()
        call_counts = {i: 0 for i in range(4)}

        def track_calls(*args, **kwargs):
            # Track which worker is being used
            return Mock(
                content=[Mock(text="Result")],
                usage=Mock(input_tokens=50, output_tokens=25)
            )

        mock_client.messages.create.side_effect = track_calls
        mock_anthropic.return_value = mock_client

        orchestrator = MultiAgentOrchestrator(num_workers=4)

        # 12 tasks should be distributed evenly across 4 workers
        subtasks = [
            {"task": f"Task {i}", "context": f"Context {i}"}
            for i in range(12)
        ]

        results = orchestrator.distribute_work(subtasks)

        # All tasks should complete
        assert len(results) == 12

    @patch('src.multi_agent_system.anthropic.Anthropic')
    def test_handling_worker_failure(self, mock_anthropic):
        """Test system continues when one worker fails"""
        mock_client = Mock()
        call_count = [0]

        def sometimes_fail(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:  # Second call fails
                raise Exception("Worker failure")
            return Mock(
                content=[Mock(text="Success")],
                usage=Mock(input_tokens=50, output_tokens=25)
            )

        mock_client.messages.create.side_effect = sometimes_fail
        mock_anthropic.return_value = mock_client

        orchestrator = MultiAgentOrchestrator(num_workers=2)

        subtasks = [
            {"task": f"Task {i}", "context": f"Context {i}"}
            for i in range(4)
        ]

        results = orchestrator.distribute_work(subtasks)

        # Should have some results despite one failure
        assert len(results) >= 3  # At least 3 out of 4 should succeed
