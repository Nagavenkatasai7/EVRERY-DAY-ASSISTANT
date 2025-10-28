# Research Assistant - Test Suite Documentation

## Overview

This directory contains a comprehensive test suite for the Research Assistant application, covering unit tests, integration tests, and end-to-end workflows.

**Total Test Coverage**: 114 tests across all application components

---

## Directory Structure

```
tests/
├── conftest.py                              # Shared fixtures and configuration
├── unit/                                    # Unit tests for individual components
│   ├── test_pdf_reference_extractor.py     # PDF reference parsing tests
│   ├── test_citation_manager.py             # Citation management tests
│   ├── test_rag_system.py                   # RAG system tests
│   └── test_web_search.py                   # Web search integration tests
├── integration/                             # Integration tests
│   └── test_multi_agent_integration.py      # Multi-agent coordination tests
└── e2e/                                     # End-to-end workflow tests
    └── test_complete_workflow.py            # Complete workflow tests
```

---

## Running Tests

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test Category

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# E2E tests only
pytest tests/e2e/ -v
```

### Run Specific Test File

```bash
pytest tests/unit/test_rag_system.py -v
```

### Run Specific Test Function

```bash
pytest tests/unit/test_rag_system.py::TestRAGSystemInitialization::test_initialization_success -v
```

### Run with Coverage Report

```bash
pytest tests/ --cov=src --cov-report=html
```

This generates an HTML coverage report in `htmlcov/index.html`

---

## Test Options

### Show Detailed Output

```bash
pytest tests/ -v --tb=long
```

### Show Short Summary

```bash
pytest tests/ --tb=short -q
```

### Stop on First Failure

```bash
pytest tests/ -x
```

### Run in Parallel (faster)

```bash
pytest tests/ -n auto
```

(Requires `pytest-xdist`: `pip install pytest-xdist`)

---

## Test Categories

### 1. Unit Tests (81 tests)

**Purpose**: Test individual components in isolation

**Components Tested**:
- PDF Reference Extractor (16 tests)
- Citation Manager (27 tests)
- RAG System (21 tests)
- Web Search (17 tests)

**What They Test**:
- Function-level behavior
- Input validation
- Error handling
- Edge cases
- Data formatting

### 2. Integration Tests (14 tests)

**Purpose**: Test component interactions

**Components Tested**:
- Multi-agent orchestration
- Agent communication
- Task distribution
- Load balancing
- Error recovery

**What They Test**:
- Cross-component data flow
- API contracts
- Coordination logic
- Concurrent operations

### 3. End-to-End Tests (19 tests)

**Purpose**: Test complete user workflows

**Workflows Tested**:
- PDF upload to report generation
- Multi-source research (PDF + Web)
- Citation tracking throughout workflow
- Error recovery and resilience
- Performance characteristics

**What They Test**:
- Complete feature flows
- Data persistence
- System integration
- Real-world scenarios

---

## Fixtures

### Available Fixtures (from `conftest.py`)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `project_root` | session | Path to project root directory |
| `test_data_dir` | session | Path to test fixtures directory |
| `temp_dir` | function | Temporary directory (auto-cleaned) |
| `mock_pdf_document` | function | Mocked PyMuPDF document |
| `sample_reference_data` | function | Sample academic reference |
| `sample_citation_data` | function | Sample citation data |
| `sample_pdf_data` | function | Sample PDF structure |
| `mock_anthropic_client` | function | Mocked Claude API client |
| `mock_tavily_client` | function | Mocked Tavily search client |
| `mock_embeddings` | function | Mocked embedding model |
| `mock_vector_store` | function | Mocked FAISS vector store |

### Using Fixtures

```python
def test_my_feature(sample_pdf_data, temp_dir):
    # Use sample_pdf_data in your test
    assert sample_pdf_data['doc_name'] == 'test_document.pdf'

    # Use temp_dir for file operations
    test_file = temp_dir / "output.txt"
    test_file.write_text("test data")
```

---

## Current Test Results

**Last Run**: 2025-10-27

| Component | Pass Rate | Status |
|-----------|-----------|--------|
| RAG System | 100% (21/21) | ✅ Excellent |
| PDF Reference Extractor | 68.8% (11/16) | ⚠️ Good |
| Citation Manager | 48.1% (13/27) | ⚠️ Needs Work |
| Web Search | 29.4% (5/17) | ❌ Issues |
| Multi-Agent System | 0% (0/14) | ❌ Not Implemented |
| E2E Workflows | 50% (6/12) | ⚠️ Mixed |
| **Overall** | **54.4% (62/114)** | ⚠️ **In Progress** |

See `TEST_REPORT.md` for detailed analysis.

---

## Writing New Tests

### Test Structure

```python
import pytest
from unittest.mock import Mock, patch

class TestMyComponent:
    """Test suite for MyComponent"""

    def test_initialization(self):
        """Test that component initializes correctly"""
        component = MyComponent()
        assert component is not None

    def test_basic_functionality(self, sample_data):
        """Test core functionality"""
        component = MyComponent()
        result = component.process(sample_data)
        assert result['success'] is True

    @patch('src.my_module.ExternalDependency')
    def test_with_mock(self, mock_external):
        """Test with mocked external dependency"""
        mock_external.return_value = Mock()
        component = MyComponent()
        component.do_something()
        mock_external.assert_called_once()
```

### Best Practices

1. **One Test, One Thing**
   - Each test should verify one specific behavior
   - Keep tests focused and simple

2. **Descriptive Names**
   - Use clear, descriptive test names
   - Format: `test_<component>_<scenario>_<expected_result>`
   - Example: `test_search_with_empty_query_returns_empty_list`

3. **Arrange-Act-Assert Pattern**
   ```python
   def test_something():
       # Arrange - set up test data
       data = create_test_data()

       # Act - perform the action
       result = function_under_test(data)

       # Assert - verify the result
       assert result == expected_value
   ```

4. **Use Fixtures for Common Setup**
   - Don't repeat setup code
   - Create fixtures in `conftest.py`
   - Use parametrized tests for multiple scenarios

5. **Mock External Dependencies**
   - Always mock API calls
   - Mock file system operations when possible
   - Mock database connections

6. **Test Edge Cases**
   - Empty inputs
   - Null/None values
   - Very large inputs
   - Malformed data
   - Concurrent operations

---

## Debugging Failed Tests

### Get Detailed Failure Information

```bash
pytest tests/unit/test_my_component.py -v --tb=long
```

### Drop into Debugger on Failure

```bash
pytest tests/ --pdb
```

### Show Print Statements

```bash
pytest tests/ -v -s
```

### Run Only Failed Tests from Last Run

```bash
pytest --lf
```

---

## Continuous Integration

### Pre-commit Checks

```bash
# Run tests before committing
pytest tests/ -v

# Check code coverage
pytest tests/ --cov=src --cov-fail-under=80
```

### GitHub Actions / CI Pipeline

Add to `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.13'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: pytest tests/ -v --cov=src
```

---

## Known Issues

### 1. Multi-Agent System Tests
**Status**: All failing (0/14 pass)
**Reason**: Components not yet implemented
**Action**: Implement `MultiAgentOrchestrator` and `WorkerAgent` classes

### 2. Web Search Tests
**Status**: Low pass rate (29.4%)
**Reason**: API mismatch between tests and implementation
**Action**: Align `WebSearchManager` with test expectations

### 3. Citation Manager Tests
**Status**: Partial pass (48.1%)
**Reason**: Missing methods (save/load, statistics, etc.)
**Action**: Complete Citation Manager API

---

## Performance Testing

### Run Performance Tests

```bash
pytest tests/e2e/test_complete_workflow.py::TestPerformance -v
```

### Benchmark Specific Functions

```python
import pytest

@pytest.mark.benchmark
def test_large_document_performance(benchmark):
    result = benchmark(process_large_document, test_data)
    assert result is not None
```

---

## Test Maintenance

### Update Tests When Code Changes

1. **API Changes**: Update test expectations
2. **New Features**: Add corresponding tests
3. **Bug Fixes**: Add regression tests
4. **Refactoring**: Ensure tests still pass

### Periodic Review

- Review test coverage monthly
- Remove obsolete tests
- Add tests for reported bugs
- Update fixtures as data models evolve

---

## Getting Help

### Test Failures

1. Check `TEST_REPORT.md` for known issues
2. Run with `-v --tb=long` for detailed errors
3. Check fixture implementations in `conftest.py`
4. Review component implementation in `src/`

### Questions

- Check pytest documentation: https://docs.pytest.org/
- Review existing test patterns in this directory
- Ask the development team

---

## Contributing

### Adding New Tests

1. Choose appropriate directory (unit/integration/e2e)
2. Follow naming convention: `test_<component>.py`
3. Use existing fixtures when possible
4. Write clear docstrings
5. Run tests locally before committing
6. Ensure new tests pass

### Test Review Checklist

- [ ] Tests have descriptive names
- [ ] Tests are independent and isolated
- [ ] External dependencies are mocked
- [ ] Edge cases are covered
- [ ] Tests pass locally
- [ ] Code coverage maintained or improved

---

**Last Updated**: 2025-10-27
**Test Framework**: pytest 8.4.2
**Python Version**: 3.13.7
**Maintained By**: Research Assistant Development Team
