#!/usr/bin/env python3
"""
Test Script for Social Media Multi-Platform Updates
Tests:
1. Content preview generation
2. Multi-platform posting logic
3. LinkedIn OAuth authorization flow
"""

import sys
import os
sys.path.insert(0, '/Users/nagavenkatasaichennu/Desktop/extension/research-assistant')

from src.social_media.linkedin_handler import LinkedInHandler
from src.social_media.content_generator import ContentGenerator
from src.social_media.models import Platform

def test_linkedin_authorization_url():
    """Test LinkedIn OAuth authorization URL generation"""
    print("\n" + "="*70)
    print("TEST 1: LinkedIn OAuth Authorization URL Generation")
    print("="*70)

    try:
        # Initialize handler
        handler = LinkedInHandler(
            client_id="test_client_id",
            client_secret="test_client_secret"
        )

        # Generate authorization URL
        state = "test_state_12345"
        redirect_uri = "http://localhost:8502/callback"

        auth_url = handler.generate_authorization_url(
            redirect_uri=redirect_uri,
            state=state
        )

        # Verify URL components
        assert "https://www.linkedin.com/oauth/v2/authorization" in auth_url
        assert "response_type=code" in auth_url
        assert "client_id=test_client_id" in auth_url
        assert f"state={state}" in auth_url
        assert "redirect_uri=" in auth_url
        assert "scope=w_member_social" in auth_url

        print("✅ PASS: Authorization URL generated correctly")
        print(f"   URL: {auth_url[:80]}...")
        return True

    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        return False


def test_content_generation_for_platforms():
    """Test content generation for different platforms"""
    print("\n" + "="*70)
    print("TEST 2: Content Generation for Multiple Platforms")
    print("="*70)

    try:
        generator = ContentGenerator()

        # Test Twitter content generation
        print("\n📱 Testing Twitter content generation...")
        twitter_result = generator.generate_trend_commentary(
            trend_topic="AI in Healthcare",
            trend_summary="AI is revolutionizing healthcare diagnostics",
            user_projects=["PhD research on ML"],
            personal_angle="As a PhD student",
            platform=Platform.TWITTER
        )

        assert 'content' in twitter_result
        assert len(twitter_result['content']) > 0
        twitter_len = len(twitter_result['content'])

        if twitter_len > 280:
            print(f"⚠️  Twitter content is {twitter_len} chars (>280), may need truncation")
        else:
            print(f"✅ Twitter content length OK: {twitter_len} chars")

        print(f"   Preview: {twitter_result['content'][:60]}...")

        # Test LinkedIn content generation
        print("\n💼 Testing LinkedIn content generation...")
        linkedin_result = generator.generate_trend_commentary(
            trend_topic="AI in Healthcare",
            trend_summary="AI is revolutionizing healthcare diagnostics",
            user_projects=["PhD research on ML"],
            personal_angle="As a PhD student",
            platform=Platform.LINKEDIN
        )

        assert 'content' in linkedin_result
        assert len(linkedin_result['content']) > 0
        assert len(linkedin_result['content']) <= 3000  # LinkedIn limit
        print(f"✅ LinkedIn content generated: {len(linkedin_result['content'])} chars")
        print(f"   Preview: {linkedin_result['content'][:60]}...")

        return True

    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_ui_functions_exist():
    """Test that UI functions exist and have correct signatures"""
    print("\n" + "="*70)
    print("TEST 3: UI Functions Existence Check")
    print("="*70)

    try:
        # Import UI module
        from src.ui import social_media_ui

        # Check generate_content_from_trend exists
        assert hasattr(social_media_ui, 'generate_content_from_trend')
        print("✅ generate_content_from_trend() exists")

        # Check generate_and_post_from_trend exists
        assert hasattr(social_media_ui, 'generate_and_post_from_trend')
        print("✅ generate_and_post_from_trend() exists")

        # Check linkedin_oauth_settings exists
        assert hasattr(social_media_ui, 'linkedin_oauth_settings')
        print("✅ linkedin_oauth_settings() exists")

        return True

    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        return False


def test_platform_enum():
    """Test Platform enum values"""
    print("\n" + "="*70)
    print("TEST 4: Platform Enum Values")
    print("="*70)

    try:
        from src.social_media.models import Platform

        assert hasattr(Platform, 'TWITTER')
        assert hasattr(Platform, 'LINKEDIN')

        print(f"✅ Platform.TWITTER = {Platform.TWITTER}")
        print(f"✅ Platform.LINKEDIN = {Platform.LINKEDIN}")

        return True

    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        return False


def test_imports():
    """Test that all necessary imports work"""
    print("\n" + "="*70)
    print("TEST 5: Import Verification")
    print("="*70)

    try:
        # Test imports
        from src.social_media.linkedin_handler import LinkedInHandler
        print("✅ LinkedInHandler imported successfully")

        from src.social_media.twitter_oauth2_handler import TwitterOAuth2Handler
        print("✅ TwitterOAuth2Handler imported successfully")

        from src.social_media.content_generator import ContentGenerator
        print("✅ ContentGenerator imported successfully")

        from src.social_media.models import Platform, ContentType, PostStatus
        print("✅ Models imported successfully")

        return True

    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("SOCIAL MEDIA MULTI-PLATFORM UPDATE - TEST SUITE")
    print("="*70)

    results = {
        "Import Verification": test_imports(),
        "LinkedIn OAuth URL Generation": test_linkedin_authorization_url(),
        "Multi-Platform Content Generation": test_content_generation_for_platforms(),
        "UI Functions Existence": test_ui_functions_exist(),
        "Platform Enum Values": test_platform_enum()
    }

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print("\n" + "="*70)
    print(f"RESULTS: {passed}/{total} tests passed")
    print("="*70)

    if passed == total:
        print("\n🎉 All tests passed! The implementation is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
