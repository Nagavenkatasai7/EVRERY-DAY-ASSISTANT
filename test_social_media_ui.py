"""
Quick test script to verify Social Media UI components
Run this to check if all dependencies are properly installed
"""

import sys
import os

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def test_import(module_name, description):
    """Test if a module can be imported"""
    try:
        __import__(module_name)
        print(f"{GREEN}✓{RESET} {description}")
        return True
    except ImportError as e:
        print(f"{RED}✗{RESET} {description}: {str(e)}")
        return False
    except Exception as e:
        print(f"{YELLOW}⚠{RESET} {description}: {str(e)}")
        return False

def test_env_var(var_name, required=True):
    """Test if environment variable is set"""
    value = os.getenv(var_name)
    if value:
        print(f"{GREEN}✓{RESET} {var_name} is configured")
        return True
    else:
        status = f"{RED}✗{RESET}" if required else f"{YELLOW}⚠{RESET}"
        print(f"{status} {var_name} not set")
        return not required

def main():
    print(f"\n{BLUE}=== Social Media UI Component Tests ==={RESET}\n")

    all_passed = True

    # Test core dependencies
    print(f"{BLUE}Testing Core Dependencies:{RESET}")
    all_passed &= test_import("streamlit", "Streamlit")
    all_passed &= test_import("pandas", "Pandas")
    all_passed &= test_import("plotly", "Plotly")
    all_passed &= test_import("anthropic", "Anthropic")
    all_passed &= test_import("tavily", "Tavily")
    all_passed &= test_import("tweepy", "Tweepy")
    all_passed &= test_import("sqlalchemy", "SQLAlchemy")
    all_passed &= test_import("cryptography", "Cryptography")
    all_passed &= test_import("apscheduler", "APScheduler")
    print()

    # Test project modules
    print(f"{BLUE}Testing Project Modules:{RESET}")
    all_passed &= test_import("src.social_media.content_generator", "Content Generator")
    all_passed &= test_import("src.social_media.trend_discovery", "Trend Discovery")
    all_passed &= test_import("src.social_media.twitter_handler", "Twitter Handler")
    all_passed &= test_import("src.social_media.scheduler", "Post Scheduler")
    all_passed &= test_import("src.social_media.models", "Database Models")
    all_passed &= test_import("src.ui.social_media_ui", "Social Media UI")
    print()

    # Test environment variables
    print(f"{BLUE}Testing Environment Configuration:{RESET}")
    all_passed &= test_env_var("ANTHROPIC_API_KEY", required=True)
    all_passed &= test_env_var("TAVILY_API_KEY", required=False)
    all_passed &= test_env_var("TWITTER_API_KEY", required=False)
    all_passed &= test_env_var("TWITTER_API_SECRET", required=False)
    print()

    # Test database initialization
    print(f"{BLUE}Testing Database:{RESET}")
    try:
        from src.social_media.models import DatabaseManager
        db = DatabaseManager()
        session = db.get_session()
        session.close()
        print(f"{GREEN}✓{RESET} Database initialized successfully")
    except Exception as e:
        print(f"{RED}✗{RESET} Database initialization failed: {str(e)}")
        all_passed = False
    print()

    # Test scheduler
    print(f"{BLUE}Testing Scheduler:{RESET}")
    try:
        from src.social_media.scheduler import PostScheduler
        scheduler = PostScheduler()
        print(f"{GREEN}✓{RESET} Scheduler initialized successfully")
        scheduler.shutdown(wait=False)
    except Exception as e:
        print(f"{RED}✗{RESET} Scheduler initialization failed: {str(e)}")
        all_passed = False
    print()

    # Summary
    print(f"{BLUE}=== Test Summary ==={RESET}")
    if all_passed:
        print(f"{GREEN}✓ All tests passed!{RESET}")
        print(f"\n{BLUE}You can now run:{RESET}")
        print(f"  streamlit run social_media_app.py")
        print(f"  OR")
        print(f"  ./start_social_media.sh")
        return 0
    else:
        print(f"{RED}✗ Some tests failed.{RESET}")
        print(f"\n{YELLOW}Action items:{RESET}")
        print(f"  1. Install missing dependencies: pip install -r requirements.txt")
        print(f"  2. Configure API keys in .env file")
        print(f"  3. Run this test again")
        return 1

if __name__ == "__main__":
    sys.exit(main())
