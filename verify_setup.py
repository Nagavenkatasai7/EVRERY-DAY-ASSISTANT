"""
Setup Verification Script
Verifies that all components are properly installed and configured
"""

import sys
from pathlib import Path
import importlib

def check_python_version():
    """Check Python version"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor}.{version.micro} (Need 3.8+)")
        return False

def check_dependencies():
    """Check if all required packages are installed"""
    print("\n📦 Checking dependencies...")

    required_packages = [
        'streamlit',
        'anthropic',
        'fitz',  # PyMuPDF
        'PIL',  # Pillow
        'langchain',
        'sentence_transformers',
        'faiss',
        'reportlab',
        'dotenv'
    ]

    all_installed = True

    for package in required_packages:
        try:
            if package == 'fitz':
                importlib.import_module('fitz')
                print(f"   ✅ PyMuPDF (fitz)")
            elif package == 'PIL':
                importlib.import_module('PIL')
                print(f"   ✅ Pillow (PIL)")
            elif package == 'dotenv':
                importlib.import_module('dotenv')
                print(f"   ✅ python-dotenv")
            else:
                importlib.import_module(package)
                print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} - NOT INSTALLED")
            all_installed = False

    return all_installed

def check_directory_structure():
    """Check if required directories exist"""
    print("\n📁 Checking directory structure...")

    base_dir = Path(__file__).parent
    required_dirs = [
        'config',
        'src',
        'utils',
        'data/uploads',
        'data/outputs',
        'data/temp',
        'logs'
    ]

    all_exist = True

    for dir_path in required_dirs:
        full_path = base_dir / dir_path
        if full_path.exists():
            print(f"   ✅ {dir_path}/")
        else:
            print(f"   ⚠️  {dir_path}/ - Creating...")
            full_path.mkdir(parents=True, exist_ok=True)
            all_exist = False

    return True  # We created missing directories

def check_env_file():
    """Check if .env file exists and has required variables"""
    print("\n🔐 Checking environment configuration...")

    base_dir = Path(__file__).parent
    env_file = base_dir / '.env'

    if not env_file.exists():
        print("   ❌ .env file not found")
        return False

    print("   ✅ .env file exists")

    # Check for required variables
    with open(env_file, 'r') as f:
        content = f.read()

    required_vars = ['ANTHROPIC_API_KEY']
    all_present = True

    for var in required_vars:
        if var in content:
            # Check if it's not empty
            if f"{var}=" in content and len(content.split(f"{var}=")[1].split('\n')[0].strip()) > 0:
                print(f"   ✅ {var} configured")
            else:
                print(f"   ⚠️  {var} is empty")
                all_present = False
        else:
            print(f"   ❌ {var} not found")
            all_present = False

    return all_present

def check_gitignore():
    """Check if .gitignore properly protects sensitive files"""
    print("\n🛡️  Checking Git security...")

    base_dir = Path(__file__).parent
    gitignore = base_dir / '.gitignore'

    if not gitignore.exists():
        print("   ❌ .gitignore not found")
        return False

    print("   ✅ .gitignore exists")

    with open(gitignore, 'r') as f:
        content = f.read()

    critical_patterns = ['.env', '*.env', 'api_keys', 'secrets']
    all_protected = True

    for pattern in critical_patterns:
        if pattern in content:
            print(f"   ✅ {pattern} protected")
        else:
            print(f"   ⚠️  {pattern} not in .gitignore")
            all_protected = False

    return all_protected

def check_imports():
    """Check if all custom modules can be imported"""
    print("\n🔧 Checking custom modules...")

    modules = [
        'config.settings',
        'src.pdf_processor',
        'src.rag_system',
        'src.claude_analyzer',
        'src.citation_manager',
        'src.report_generator',
        'utils.logger',
        'utils.exceptions',
        'utils.file_utils',
        'utils.image_utils'
    ]

    all_importable = True

    for module in modules:
        try:
            importlib.import_module(module)
            print(f"   ✅ {module}")
        except Exception as e:
            print(f"   ❌ {module} - {str(e)}")
            all_importable = False

    return all_importable

def test_claude_connection():
    """Test connection to Claude API"""
    print("\n🤖 Testing Claude API connection...")

    try:
        from dotenv import load_dotenv
        import os
        import anthropic

        load_dotenv()
        api_key = os.getenv('ANTHROPIC_API_KEY')

        if not api_key:
            print("   ❌ API key not found in environment")
            return False

        client = anthropic.Anthropic(api_key=api_key)

        # Simple test message
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=50,
            messages=[{"role": "user", "content": "Reply with 'OK' only."}]
        )

        if response and response.content:
            print("   ✅ Claude API connection successful")
            return True
        else:
            print("   ❌ Claude API returned empty response")
            return False

    except anthropic.AuthenticationError:
        print("   ❌ Authentication failed - Invalid API key")
        return False
    except anthropic.APIError as e:
        print(f"   ❌ API Error: {str(e)}")
        return False
    except Exception as e:
        print(f"   ❌ Connection test failed: {str(e)}")
        return False

def main():
    """Run all verification checks"""
    print("=" * 60)
    print("🔍 AI Research Assistant - Setup Verification")
    print("=" * 60)

    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Directory Structure", check_directory_structure),
        ("Environment File", check_env_file),
        ("Git Security", check_gitignore),
        ("Custom Modules", check_imports),
        ("Claude API", test_claude_connection)
    ]

    results = []

    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"   ❌ Error running check: {str(e)}")
            results.append((check_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:12} {check_name}")

    print("-" * 60)
    print(f"Result: {passed}/{total} checks passed")

    if passed == total:
        print("\n🎉 All checks passed! Application is ready to run.")
        print("\nTo start the application, run:")
        print("   streamlit run app.py")
    else:
        print("\n⚠️  Some checks failed. Please review the issues above.")
        if not results[1][1]:  # Dependencies check failed
            print("\nTo install dependencies, run:")
            print("   pip install -r requirements.txt")

    print("=" * 60)

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
