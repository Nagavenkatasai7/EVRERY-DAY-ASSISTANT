#!/usr/bin/env python3
"""
Standalone launcher for Social Media Automation UI
Run this file directly to access the social media automation interface
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the UI
from src.ui.social_media_ui import social_media_automation_page

if __name__ == "__main__":
    social_media_automation_page()
