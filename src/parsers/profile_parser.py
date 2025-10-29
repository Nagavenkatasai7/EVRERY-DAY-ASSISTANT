"""
Profile data parser to extract structured information from Profile.pdf
"""
from pypdf import PdfReader
from pathlib import Path
import re
import json

class ProfileParser:
    def __init__(self, profile_pdf_path="Profile.pdf"):
        self.profile_pdf_path = profile_pdf_path
        self.profile_data = None

    def extract_text_from_pdf(self):
        """Extract text from Profile.pdf"""
        try:
            reader = PdfReader(self.profile_pdf_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            print(f"Error reading profile PDF: {e}")
            return ""

    def parse_profile(self):
        """Parse profile text into structured data"""
        text = self.extract_text_from_pdf()

        if not text:
            return None

        # Initialize profile structure
        profile = {
            "personal_info": {},
            "summary": "",
            "experience": [],
            "education": [],
            "skills": [],
            "certifications": [],
            "projects": [],
            "raw_text": text
        }

        # Extract personal information (name, email, phone, location, linkedin, etc.)
        # This is a simplified parser - you may need to customize based on your Profile.pdf structure
        lines = text.split('\n')

        # Try to extract email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            profile["personal_info"]["email"] = emails[0]

        # Try to extract phone
        phone_pattern = r'[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}'
        phones = re.findall(phone_pattern, text)
        if phones:
            profile["personal_info"]["phone"] = phones[0]

        # Try to extract LinkedIn
        linkedin_pattern = r'linkedin\.com/in/[A-Za-z0-9-]+'
        linkedins = re.findall(linkedin_pattern, text)
        if linkedins:
            profile["personal_info"]["linkedin"] = linkedins[0]

        # Try to extract GitHub
        github_pattern = r'github\.com/[A-Za-z0-9-]+'
        githubs = re.findall(github_pattern, text)
        if githubs:
            profile["personal_info"]["github"] = githubs[0]

        # Store the profile data
        self.profile_data = profile

        return profile

    def get_profile_summary(self):
        """Get a text summary of the profile for use in prompts"""
        if not self.profile_data:
            self.parse_profile()

        if not self.profile_data:
            return ""

        # Return the raw text for now - Claude can extract what it needs
        return self.profile_data.get("raw_text", "")

    def save_profile_json(self, output_path="profile_data.json"):
        """Save parsed profile as JSON"""
        if not self.profile_data:
            self.parse_profile()

        if self.profile_data:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.profile_data, f, indent=2)
            return output_path

        return None

def main():
    """Test the profile parser"""
    parser = ProfileParser()
    profile = parser.parse_profile()

    if profile:
        print("✓ Profile parsed successfully")
        print(f"\nPersonal Info:")
        for key, value in profile["personal_info"].items():
            print(f"  {key}: {value}")

        # Save to JSON
        output_file = parser.save_profile_json()
        if output_file:
            print(f"\n✓ Profile data saved to {output_file}")

        print(f"\nProfile text length: {len(profile['raw_text'])} characters")
    else:
        print("✗ Failed to parse profile")

if __name__ == "__main__":
    main()
