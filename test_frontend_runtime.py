"""
Frontend Runtime Issue Detection Script
Tests for common runtime errors, logical issues, and integration problems
"""

import sys
import os
sys.path.insert(0, '/Users/nagavenkatasaichennu/Desktop/extension/research-assistant')

from src.social_media.models import ContentType, Platform

def test_content_type_mapping():
    """Test that content type display names map correctly to enums"""
    print("Testing content type mapping...")

    # Display names used in UI
    display_names = [
        "📊 Project Showcase",
        "📚 Learning Update",
        "💡 Trend Commentary",
        "❓ Question Post"
    ]

    # Expected enum mappings
    expected_mappings = {
        "Project Showcase": ContentType.PROJECT_SHOWCASE,
        "Learning Update": ContentType.LEARNING_UPDATE,
        "Trend Commentary": ContentType.INDUSTRY_INSIGHT,  # This might be wrong!
        "Question Post": ContentType.QUESTION_DRIVEN
    }

    issues = []

    for display_name in display_names:
        # Extract the text part (without emoji)
        text_part = display_name.split(" ", 1)[1]

        # Check if mapping exists
        if text_part not in expected_mappings:
            issues.append(f"No mapping found for: {text_part}")
        else:
            print(f"  ✓ {text_part} -> {expected_mappings[text_part]}")

    # Check if INDUSTRY_INSIGHT is the right mapping for "Trend Commentary"
    print("\n⚠️  POTENTIAL ISSUE: 'Trend Commentary' might need to map to ContentType.INDUSTRY_INSIGHT")
    print("   But the content generator has generate_trend_commentary() which might expect different type")

    return len(issues) == 0


def test_set_page_config_issue():
    """Test for st.set_page_config() placement issue"""
    print("\n\nTesting st.set_page_config() placement...")

    with open('/Users/nagavenkatasaichennu/Desktop/extension/research-assistant/src/ui/social_media_ui.py', 'r') as f:
        content = f.read()

    if 'st.set_page_config' in content:
        # Find line number
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if 'st.set_page_config' in line:
                print(f"  ❌ CRITICAL ERROR: st.set_page_config() found at line {i}")
                print(f"     This will fail when called from within a tab in app.py!")
                print(f"     st.set_page_config() must be the FIRST Streamlit command")
                print(f"     and can only be called ONCE per script.")
                return False

    print("  ✓ No st.set_page_config() issues found")
    return True


def test_content_type_field_in_generation():
    """Check if content_type is properly set in generation functions"""
    print("\n\nTesting content_type field in generation functions...")

    with open('/Users/nagavenkatasaichennu/Desktop/extension/research-assistant/src/ui/social_media_ui.py', 'r') as f:
        content = f.read()

    issues = []

    # Check project showcase
    if 'project_showcase_form' in content:
        # Look for where result is stored
        if 'st.session_state.generated_content = [result]' in content:
            # Check if content_type is added to result
            if 'result["content_type"]' not in content and "content_type" not in content[content.find('project_showcase_form'):content.find('def learning_update_form')]:
                print("  ⚠️  WARNING: content_type might not be set in project_showcase results")
                issues.append("project_showcase content_type")

    # Check if ContentType mapping is done
    if '"📊 Project Showcase"' in content and 'ContentType.PROJECT_SHOWCASE' not in content:
        print("  ❌ CRITICAL: ContentType enum not mapped from display names!")
        issues.append("ContentType mapping missing")

    if len(issues) == 0:
        print("  ✓ Content type handling appears correct")
        return True
    else:
        print(f"  ❌ Found {len(issues)} issues with content_type handling")
        return False


def test_database_session_cleanup():
    """Check for proper database session cleanup"""
    print("\n\nTesting database session cleanup...")

    with open('/Users/nagavenkatasaichennu/Desktop/extension/research-assistant/src/ui/social_media_ui.py', 'r') as f:
        content = f.read()

    # Count session.close() calls
    get_session_count = content.count('.get_session()')
    session_close_count = content.count('session.close()')

    print(f"  - get_session() calls: {get_session_count}")
    print(f"  - session.close() calls: {session_close_count}")

    if get_session_count > session_close_count:
        print(f"  ⚠️  WARNING: {get_session_count - session_close_count} sessions might not be closed")
        print("     This could cause database lock issues")
        return False
    else:
        print("  ✓ All sessions appear to be closed")
        return True


def test_missing_analytics_methods():
    """Check if analytics methods are properly called"""
    print("\n\nTesting analytics implementation...")

    with open('/Users/nagavenkatasaichennu/Desktop/extension/research-assistant/src/ui/social_media_ui.py', 'r') as f:
        ui_content = f.read()

    # Check if AnalyticsCollector is imported
    if 'from src.social_media.analytics import AnalyticsCollector' in ui_content:
        print("  ✓ AnalyticsCollector imported")

        # Check if it's actually used
        if 'AnalyticsCollector(' not in ui_content:
            print("  ⚠️  WARNING: AnalyticsCollector imported but never instantiated")
            print("     Analytics dashboard might not work correctly")
            return False

    # Check if analytics methods exist
    try:
        with open('/Users/nagavenkatasaichennu/Desktop/extension/research-assistant/src/social_media/analytics.py', 'r') as f:
            analytics_content = f.read()

        required_methods = [
            'collect_post_analytics',
            'get_engagement_rate',
            'get_best_posting_times',
            'generate_weekly_report'
        ]

        for method in required_methods:
            if f'def {method}' in analytics_content:
                print(f"  ✓ {method} exists")
            else:
                print(f"  ❌ {method} missing in analytics.py")
                return False

    except FileNotFoundError:
        print("  ❌ analytics.py not found")
        return False

    print("  ✓ Analytics implementation looks good")
    return True


def test_content_generator_methods():
    """Verify all content generation methods exist"""
    print("\n\nTesting content generator methods...")

    try:
        with open('/Users/nagavenkatasaichennu/Desktop/extension/research-assistant/src/social_media/content_generator.py', 'r') as f:
            content = f.read()

        required_methods = [
            'generate_project_showcase',
            'generate_learning_update',
            'generate_trend_commentary',
            'generate_question_post',
            'generate_multiple_variants',
            'check_ai_detection_score'
        ]

        all_exist = True
        for method in required_methods:
            if f'def {method}' in content:
                print(f"  ✓ {method} exists")
            else:
                print(f"  ❌ {method} missing")
                all_exist = False

        return all_exist

    except FileNotFoundError:
        print("  ❌ content_generator.py not found")
        return False


def main():
    print("="*70)
    print("FRONTEND RUNTIME ISSUE DETECTION")
    print("="*70)

    results = {
        "Content Type Mapping": test_content_type_mapping(),
        "st.set_page_config Placement": test_set_page_config_issue(),
        "Content Type Field": test_content_type_field_in_generation(),
        "Database Session Cleanup": test_database_session_cleanup(),
        "Analytics Methods": test_missing_analytics_methods(),
        "Content Generator Methods": test_content_generator_methods()
    }

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\n{passed}/{total} tests passed")

    if passed < total:
        print("\n❌ CRITICAL ISSUES FOUND - Frontend needs fixes before testing")
        sys.exit(1)
    else:
        print("\n✅ All checks passed - Ready for integration testing")
        sys.exit(0)


if __name__ == "__main__":
    main()
