"""
PDF generation engine - converts markdown resume to ATS-friendly PDF
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfgen import canvas
from pathlib import Path
import re

class PDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom ATS-friendly styles"""
        # Header style for name
        self.styles.add(ParagraphStyle(
            name='CustomName',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor='#000000',
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        # Contact info style
        self.styles.add(ParagraphStyle(
            name='CustomContact',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor='#000000',
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica'
        ))

        # Section header style
        self.styles.add(ParagraphStyle(
            name='CustomSectionHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor='#000000',
            spaceAfter=6,
            spaceBefore=12,
            fontName='Helvetica-Bold',
            borderWidth=0,
            borderPadding=0,
            borderColor='#000000',
            backColor=None
        ))

        # Job title style
        self.styles.add(ParagraphStyle(
            name='CustomJobTitle',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor='#000000',
            spaceAfter=3,
            fontName='Helvetica-Bold'
        ))

        # Normal text style
        self.styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor='#000000',
            spaceAfter=6,
            fontName='Helvetica',
            leading=14
        ))

        # Bullet style
        self.styles.add(ParagraphStyle(
            name='CustomBullet',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor='#000000',
            spaceAfter=3,
            fontName='Helvetica',
            leftIndent=20,
            bulletIndent=10,
            leading=13
        ))

    def markdown_to_pdf(self, markdown_content, output_path):
        """
        Convert markdown resume to ATS-friendly PDF

        Args:
            markdown_content: Resume in markdown format
            output_path: Path to save PDF
        """
        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )

        # Parse markdown and build story
        story = self._parse_markdown(markdown_content)

        # Build PDF
        doc.build(story)

        return output_path

    def _parse_markdown(self, markdown_content):
        """Parse markdown content into ReportLab story elements"""
        story = []
        lines = markdown_content.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Skip empty lines
            if not line:
                story.append(Spacer(1, 6))
                i += 1
                continue

            # H1 - Candidate Name
            if line.startswith('# '):
                name = line[2:].strip()
                story.append(Paragraph(name, self.styles['CustomName']))
                i += 1
                continue

            # H2 - Section Headers
            if line.startswith('## '):
                header = line[3:].strip()
                story.append(Spacer(1, 6))
                story.append(Paragraph(header.upper(), self.styles['CustomSectionHeader']))
                i += 1
                continue

            # H3 - Job Titles/Subsections
            if line.startswith('### '):
                title = line[4:].strip()
                story.append(Paragraph(title, self.styles['CustomJobTitle']))
                i += 1
                continue

            # Italic text (usually dates/locations)
            if line.startswith('*') and line.endswith('*'):
                text = line[1:-1].strip()
                story.append(Paragraph(f"<i>{text}</i>", self.styles['CustomNormal']))
                i += 1
                continue

            # Bullet points
            if line.startswith('- ') or line.startswith('• '):
                bullet_text = line[2:].strip()
                # Clean up any markdown formatting
                bullet_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', bullet_text)
                bullet_text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', bullet_text)
                story.append(Paragraph(f"• {bullet_text}", self.styles['CustomBullet']))
                i += 1
                continue

            # Pipe separator (contact info line)
            if '|' in line and i < 5:  # Contact info usually in first few lines
                # Contact info line - make LinkedIn, GitHub, and Portfolio clickable
                contact_line = line.replace('|', ' | ')

                # Add hyperlinks for LinkedIn, GitHub, and Portfolio
                contact_line = contact_line.replace('LinkedIn', '<link href="https://linkedin.com/in/naga-venkata-sai-chennu" color="blue"><u>LinkedIn</u></link>')
                contact_line = contact_line.replace('GitHub', '<link href="https://github.com/nagavenkatasai7" color="blue"><u>GitHub</u></link>')
                contact_line = contact_line.replace('Portfolio', '<link href="https://nagavenkatasai7.github.io/portfolio/" color="blue"><u>Portfolio</u></link>')

                story.append(Paragraph(contact_line, self.styles['CustomContact']))
                i += 1
                continue

            # Regular paragraph
            if line:
                # Clean up markdown formatting
                text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
                text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
                story.append(Paragraph(text, self.styles['CustomNormal']))

            i += 1

        return story

def main():
    """Test PDF generator"""
    sample_markdown = """# John Doe
johndoe@email.com | (555) 123-4567 | linkedin.com/in/johndoe | github.com/johndoe | San Francisco, CA

## PROFESSIONAL SUMMARY
Senior Software Engineer with 5+ years of experience in AI/ML and full-stack development. Specialized in building scalable RAG systems and LLM applications using Python, LangChain, and cloud technologies.

## TECHNICAL SKILLS
**Programming:** Python, JavaScript, TypeScript, SQL
**AI/ML:** LangChain, OpenAI, Anthropic Claude, RAG, Prompt Engineering
**Cloud:** AWS, Docker, Kubernetes
**Databases:** PostgreSQL, MongoDB, Pinecone

## PROFESSIONAL EXPERIENCE

### Senior AI Engineer | TechCorp | San Francisco, CA
*01/2022 - Present*
- Built production RAG system handling 10K+ queries/day with 95% accuracy
- Implemented LLM-powered features using GPT-4 and Claude, reducing support costs by 40%
- Led team of 3 engineers in developing AI platform serving 50K+ users

### Software Engineer | StartupXYZ | Remote
*06/2019 - 12/2021*
- Developed full-stack applications using React and Node.js
- Implemented CI/CD pipelines reducing deployment time by 60%

## EDUCATION
Master of Science in Computer Science | Stanford University | 2019
Bachelor of Science in Computer Science | UC Berkeley | 2017

## CERTIFICATIONS
AWS Certified Solutions Architect - Professional
"""

    generator = PDFGenerator()
    output_path = "test_resume.pdf"

    try:
        generator.markdown_to_pdf(sample_markdown, output_path)
        print(f"✓ PDF generated successfully: {output_path}")
    except Exception as e:
        print(f"✗ PDF generation failed: {e}")

if __name__ == "__main__":
    main()
