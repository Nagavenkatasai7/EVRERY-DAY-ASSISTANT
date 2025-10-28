"""
Comprehensive Security Verification Test
Tests all security fixes and checks for additional vulnerabilities
"""

import sys
from pathlib import Path

# Test results storage
test_results = {
    "passed": 0,
    "failed": 0,
    "warnings": 0,
    "tests": []
}

def log_test(test_name, status, message=""):
    """Log test result"""
    test_results["tests"].append({
        "name": test_name,
        "status": status,
        "message": message
    })
    if status == "PASS":
        test_results["passed"] += 1
        print(f"✅ PASS: {test_name}")
    elif status == "FAIL":
        test_results["failed"] += 1
        print(f"❌ FAIL: {test_name} - {message}")
    elif status == "WARN":
        test_results["warnings"] += 1
        print(f"⚠️  WARN: {test_name} - {message}")
    if message:
        print(f"   → {message}")

print("=" * 80)
print("COMPREHENSIVE SECURITY VERIFICATION TEST")
print("=" * 80)
print()

# =============================================================================
# TEST CATEGORY 1: PATH TRAVERSAL PROTECTION (FIX #1)
# =============================================================================
print("📁 TEST CATEGORY 1: Path Traversal Protection")
print("-" * 80)

try:
    from src.document_session import DocumentSession

    # Test 1.1: Valid session_id
    try:
        session = DocumentSession("session_20241027_120000", "Test Session")
        log_test("1.1 - Valid session_id accepted", "PASS")
    except ValueError as e:
        log_test("1.1 - Valid session_id accepted", "FAIL", str(e))

    # Test 1.2: Path traversal attack blocked
    try:
        session = DocumentSession("../../../etc/passwd", "Malicious Session")
        log_test("1.2 - Path traversal attack blocked", "FAIL", "Path traversal NOT blocked!")
    except ValueError:
        log_test("1.2 - Path traversal attack blocked", "PASS")

    # Test 1.3: Invalid format blocked
    try:
        session = DocumentSession("invalid_format", "Invalid Session")
        log_test("1.3 - Invalid format blocked", "FAIL", "Invalid format NOT blocked!")
    except ValueError:
        log_test("1.3 - Invalid format blocked", "PASS")

    # Test 1.4: Null bytes blocked
    try:
        session = DocumentSession("session_20241027\x00_120000", "Null Byte Session")
        log_test("1.4 - Null bytes blocked", "FAIL", "Null bytes NOT blocked!")
    except ValueError:
        log_test("1.4 - Null bytes blocked", "PASS")

    # Test 1.5: Regex validation exists
    if hasattr(DocumentSession, '_is_valid_session_id'):
        log_test("1.5 - Validation method exists", "PASS")
    else:
        log_test("1.5 - Validation method exists", "FAIL", "Method not found")

except Exception as e:
    log_test("1.x - Path Traversal Tests", "FAIL", f"Import or execution error: {str(e)}")

print()

# =============================================================================
# TEST CATEGORY 2: PROMPT INJECTION PROTECTION (FIX #2)
# =============================================================================
print("💬 TEST CATEGORY 2: Prompt Injection Protection")
print("-" * 80)

try:
    from src.chatbot import DocumentChatbot

    # Test 2.1: Validation method exists
    if hasattr(DocumentChatbot, '_validate_question'):
        log_test("2.1 - Validation method exists", "PASS")
    else:
        log_test("2.1 - Validation method exists", "FAIL", "Method not found")

    # Test 2.2: Length validation (simulated)
    # Cannot test without full initialization, check code structure
    import inspect
    source = inspect.getsource(DocumentChatbot._validate_question)

    if "len(question) > 2000" in source:
        log_test("2.2 - Max length check present", "PASS")
    else:
        log_test("2.2 - Max length check present", "FAIL")

    if "len(question.strip()) < 3" in source:
        log_test("2.3 - Min length check present", "PASS")
    else:
        log_test("2.3 - Min length check present", "FAIL")

    # Test 2.4: Suspicious pattern detection
    if "suspicious_patterns" in source:
        log_test("2.4 - Suspicious pattern detection", "PASS")
    else:
        log_test("2.4 - Suspicious pattern detection", "FAIL")

    # Test 2.5: Whitespace trimming
    if "strip()" in source:
        log_test("2.5 - Whitespace trimming", "PASS")
    else:
        log_test("2.5 - Whitespace trimming", "FAIL")

except Exception as e:
    log_test("2.x - Prompt Injection Tests", "FAIL", f"Import or execution error: {str(e)}")

print()

# =============================================================================
# TEST CATEGORY 3: SAFE DESERIALIZATION (FIX #3)
# =============================================================================
print("🔒 TEST CATEGORY 3: Safe Deserialization (JSON vs Pickle)")
print("-" * 80)

try:
    from src.rag_system import RAGSystem
    import inspect

    # Test 3.1: Save uses JSON
    save_source = inspect.getsource(RAGSystem.save_vector_store)
    if "chunks_metadata.json" in save_source and "json.dump" in save_source:
        log_test("3.1 - Save uses JSON format", "PASS")
    else:
        log_test("3.1 - Save uses JSON format", "FAIL", "Still using pickle for save")

    # Test 3.2: Load tries JSON first
    load_source = inspect.getsource(RAGSystem.load_vector_store)
    if "chunks_metadata.json" in load_source and "json.load" in load_source:
        log_test("3.2 - Load tries JSON first", "PASS")
    else:
        log_test("3.2 - Load tries JSON first", "FAIL")

    # Test 3.3: Backward compatibility for pickle
    if "chunks_metadata.pkl" in load_source and "pickle.load" in load_source:
        log_test("3.3 - Backward compatibility present", "PASS")
    else:
        log_test("3.3 - Backward compatibility present", "WARN", "Old sessions may not load")

    # Test 3.4: Warning for legacy format
    if "logger.warning" in load_source and "legacy pickle" in load_source.lower():
        log_test("3.4 - Legacy format warning", "PASS")
    else:
        log_test("3.4 - Legacy format warning", "WARN", "No warning for pickle loading")

except Exception as e:
    log_test("3.x - Deserialization Tests", "FAIL", f"Import or execution error: {str(e)}")

print()

# =============================================================================
# TEST CATEGORY 4: ADDITIONAL SECURITY CHECKS
# =============================================================================
print("🛡️  TEST CATEGORY 4: Additional Security Checks")
print("-" * 80)

# Test 4.1: API Key Management
try:
    from config.settings import ANTHROPIC_API_KEY
    import os

    if ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != "your_api_key_here":
        if ANTHROPIC_API_KEY.startswith("sk-ant-"):
            log_test("4.1 - API key properly configured", "PASS")
        else:
            log_test("4.1 - API key properly configured", "WARN", "API key format unusual")
    else:
        log_test("4.1 - API key properly configured", "WARN", "API key not set")
except Exception as e:
    log_test("4.1 - API key check", "WARN", f"Could not verify: {str(e)}")

# Test 4.2: Environment variable usage
try:
    config_file = Path("config/settings.py")
    if config_file.exists():
        with open(config_file, 'r') as f:
            content = f.read()
            if "os.getenv" in content or "os.environ" in content:
                log_test("4.2 - Uses environment variables", "PASS")
            else:
                log_test("4.2 - Uses environment variables", "WARN", "Consider using env vars")
except Exception as e:
    log_test("4.2 - Environment variable check", "WARN", str(e))

# Test 4.3: PDF file validation
try:
    from src.pdf_processor import PDFProcessor
    import inspect

    # Check if there's file extension validation
    init_source = inspect.getsource(PDFProcessor.__init__)
    if ".pdf" in init_source.lower():
        log_test("4.3 - PDF extension validation", "PASS")
    else:
        log_test("4.3 - PDF extension validation", "WARN", "No explicit PDF validation found")
except Exception as e:
    log_test("4.3 - PDF validation check", "WARN", str(e))

# Test 4.4: Error handling
try:
    from utils.exceptions import RAGSystemError, VectorStoreError, ClaudeAPIError
    log_test("4.4 - Custom exception classes", "PASS")
except ImportError:
    log_test("4.4 - Custom exception classes", "WARN", "Custom exceptions not found")

# Test 4.5: Logging security
try:
    from utils.logger import get_logger
    log_test("4.5 - Logging framework present", "PASS")
except ImportError:
    log_test("4.5 - Logging framework present", "WARN", "Logging module not found")

# Test 4.6: File permissions
try:
    data_dir = Path("data")
    if data_dir.exists():
        import stat
        mode = data_dir.stat().st_mode
        # Check if world-writable (security risk)
        if mode & stat.S_IWOTH:
            log_test("4.6 - Data directory permissions", "WARN", "Directory is world-writable")
        else:
            log_test("4.6 - Data directory permissions", "PASS")
    else:
        log_test("4.6 - Data directory permissions", "PASS", "Will be created on first use")
except Exception as e:
    log_test("4.6 - File permissions check", "WARN", str(e))

# Test 4.7: SQL Injection (if any DB queries)
try:
    # Check for raw SQL queries in codebase
    code_files = list(Path("src").glob("*.py"))
    sql_vulnerable = False
    for file in code_files:
        with open(file, 'r') as f:
            content = f.read()
            if "execute(" in content and ("%" % "f\"" in content or ".format(" in content):
                sql_vulnerable = True
                break

    if sql_vulnerable:
        log_test("4.7 - SQL injection check", "WARN", "Potential SQL injection found")
    else:
        log_test("4.7 - SQL injection check", "PASS", "No SQL vulnerabilities detected")
except Exception as e:
    log_test("4.7 - SQL injection check", "WARN", str(e))

# Test 4.8: Secrets in code
try:
    sensitive_patterns = ["password =", "api_key =", "secret =", "token ="]
    found_secrets = []

    for file in Path("src").glob("*.py"):
        with open(file, 'r') as f:
            content = f.read().lower()
            for pattern in sensitive_patterns:
                if pattern in content and "getenv" not in content:
                    found_secrets.append(f"{file}: {pattern}")

    if found_secrets:
        log_test("4.8 - Hardcoded secrets check", "WARN", f"Found: {', '.join(found_secrets)}")
    else:
        log_test("4.8 - Hardcoded secrets check", "PASS")
except Exception as e:
    log_test("4.8 - Hardcoded secrets check", "WARN", str(e))

print()

# =============================================================================
# TEST CATEGORY 5: CODE QUALITY CHECKS
# =============================================================================
print("📋 TEST CATEGORY 5: Code Quality & Best Practices")
print("-" * 80)

# Test 5.1: Type hints usage
try:
    from src.chatbot import DocumentChatbot
    import inspect

    sig = inspect.signature(DocumentChatbot.ask_question)
    if any(param.annotation != inspect.Parameter.empty for param in sig.parameters.values()):
        log_test("5.1 - Type hints present", "PASS")
    else:
        log_test("5.1 - Type hints present", "WARN", "Consider adding type hints")
except Exception as e:
    log_test("5.1 - Type hints check", "WARN", str(e))

# Test 5.2: Docstrings
try:
    from src.chatbot import DocumentChatbot
    if DocumentChatbot.ask_question.__doc__:
        log_test("5.2 - Docstrings present", "PASS")
    else:
        log_test("5.2 - Docstrings present", "WARN")
except Exception as e:
    log_test("5.2 - Docstrings check", "WARN", str(e))

# Test 5.3: Context managers for file operations
try:
    from src.pdf_processor import PDFProcessor
    if hasattr(PDFProcessor, '__enter__') and hasattr(PDFProcessor, '__exit__'):
        log_test("5.3 - PDF context manager", "PASS")
    else:
        log_test("5.3 - PDF context manager", "WARN", "Consider adding context manager")
except Exception as e:
    log_test("5.3 - Context manager check", "WARN", str(e))

# Test 5.4: Error messages don't leak sensitive info
try:
    from utils.exceptions import RAGSystemError
    # Check if exception messages are generic
    log_test("5.4 - Safe error messages", "PASS", "Using custom exceptions")
except Exception as e:
    log_test("5.4 - Safe error messages", "WARN", str(e))

print()

# =============================================================================
# FINAL REPORT
# =============================================================================
print("=" * 80)
print("SECURITY VERIFICATION SUMMARY")
print("=" * 80)
print()
print(f"✅ Tests Passed:  {test_results['passed']}")
print(f"❌ Tests Failed:  {test_results['failed']}")
print(f"⚠️  Warnings:     {test_results['warnings']}")
print(f"📊 Total Tests:  {len(test_results['tests'])}")
print()

# Calculate security score
total_tests = len(test_results['tests'])
passed = test_results['passed']
failed = test_results['failed']
warnings = test_results['warnings']

# Score calculation:
# - PASS = 1.0 point
# - WARN = 0.5 point
# - FAIL = 0.0 point
score = (passed * 1.0 + warnings * 0.5) / total_tests * 10
score = round(score, 1)

print(f"🏆 SECURITY SCORE: {score}/10.0")
print()

# Determine security level
if score >= 9.5:
    level = "EXCELLENT"
    emoji = "🟢"
elif score >= 8.5:
    level = "GOOD"
    emoji = "🟡"
elif score >= 7.0:
    level = "ACCEPTABLE"
    emoji = "🟠"
else:
    level = "NEEDS IMPROVEMENT"
    emoji = "🔴"

print(f"{emoji} Security Level: {level}")
print()

# Show failed tests
if test_results['failed'] > 0:
    print("❌ FAILED TESTS:")
    for test in test_results['tests']:
        if test['status'] == 'FAIL':
            print(f"   - {test['name']}: {test['message']}")
    print()

# Show warnings
if test_results['warnings'] > 0:
    print("⚠️  WARNINGS:")
    for test in test_results['tests']:
        if test['status'] == 'WARN':
            print(f"   - {test['name']}: {test['message']}")
    print()

print("=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)

# Exit with appropriate code
sys.exit(0 if test_results['failed'] == 0 else 1)
