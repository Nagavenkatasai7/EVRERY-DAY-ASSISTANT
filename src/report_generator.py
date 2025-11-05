"""
Report Generator
Generates professional PDF reports with analysis, citations, and images
"""

from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
    PageBreak, Table, TableStyle, KeepTogether
)
from reportlab.pdfgen import canvas

from config.settings import (
    REPORT_PAGE_SIZE,
    REPORT_FONT_SIZE,
    REPORT_TITLE_SIZE,
    REPORT_HEADING_SIZE,
    OUTPUT_DIR
)
from utils.logger import get_logger
from utils.exceptions import ReportGenerationError

logger = get_logger(__name__)


class PageNumCanvas(canvas.Canvas):
    """Custom canvas for adding page numbers"""

    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self.pages = []

    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self.pages)
        for page_num, page in enumerate(self.pages, start=1):
            self.__dict__.update(page)
            self.draw_page_number(page_num, page_count)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_num, page_count):
        self.setFont("Helvetica", 9)
        self.setFillColor(HexColor("#7f8c8d"))
        self.drawRightString(
            7.5 * inch,
            0.5 * inch,
            f"Page {page_num} of {page_count}"
        )


class ReportGenerator:
    """
    Generates professional PDF reports from research analysis
    """

    def __init__(self):
        """Initialize report generator"""
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()
        logger.info("Report generator initialized")

    def _create_custom_styles(self):
        """Create custom paragraph styles"""

        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=REPORT_TITLE_SIZE,
            textColor=HexColor('#2c3e50'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        # Heading style
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=REPORT_HEADING_SIZE,
            textColor=HexColor('#34495e'),
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        ))

        # Subheading style
        self.styles.add(ParagraphStyle(
            name='CustomSubheading',
            parent=self.styles['Heading3'],
            fontSize=13,
            textColor=HexColor('#34495e'),
            spaceAfter=10,
            spaceBefore=15,
            fontName='Helvetica-Bold'
        ))

        # Body style
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['BodyText'],
            fontSize=REPORT_FONT_SIZE,
            alignment=TA_JUSTIFY,
            spaceAfter=12,
            leading=16
        ))

        # Citation style
        self.styles.add(ParagraphStyle(
            name='Citation',
            parent=self.styles['BodyText'],
            fontSize=9,
            textColor=HexColor('#7f8c8d'),
            leftIndent=20,
            spaceAfter=6,
            fontName='Helvetica-Oblique'
        ))

        # Caption style
        self.styles.add(ParagraphStyle(
            name='Caption',
            parent=self.styles['BodyText'],
            fontSize=9,
            textColor=HexColor('#5d6d7e'),
            alignment=TA_CENTER,
            spaceAfter=12,
            fontName='Helvetica-Oblique'
        ))

        # Metadata style
        self.styles.add(ParagraphStyle(
            name='Metadata',
            parent=self.styles['BodyText'],
            fontSize=10,
            textColor=HexColor('#5d6d7e'),
            alignment=TA_CENTER,
            spaceAfter=20
        ))

    def generate_report(
        self,
        title: str,
        sections: List[Dict],
        bibliography: List[Dict],
        metadata: Optional[Dict] = None,
        output_filename: Optional[str] = None
    ) -> Path:
        """
        Generate comprehensive PDF report

        Args:
            title: Report title
            sections: List of section dictionaries with content
            bibliography: List of bibliography entries
            metadata: Optional metadata dictionary
            output_filename: Optional output filename

        Returns:
            Path to generated PDF

        Raises:
            ReportGenerationError: If generation fails
        """
        try:
            logger.info(f"Generating report: {title}")

            # Create output filename
            if not output_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_'))
                safe_title = safe_title.replace(' ', '_')[:50]
                output_filename = f"{safe_title}_{timestamp}.pdf"

            output_path = OUTPUT_DIR / output_filename

            # Create PDF document
            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )

            # Build story
            story = []

            # Title page
            story.extend(self._create_title_page(title, metadata))

            # Table of contents
            story.append(PageBreak())
            story.extend(self._create_table_of_contents(sections))

            # Main content
            story.append(PageBreak())
            story.extend(self._create_content_sections(sections))

            # Bibliography
            if bibliography:
                story.append(PageBreak())
                story.extend(self._create_bibliography(bibliography))

            # Build PDF with custom canvas
            doc.build(story, canvasmaker=PageNumCanvas)

            logger.info(f"Report generated successfully: {output_path.name}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate report: {str(e)}")
            raise ReportGenerationError(f"Report generation failed: {str(e)}")

    def _create_title_page(self, title: str, metadata: Optional[Dict]) -> List:
        """Create title page elements"""
        elements = []

        # Add logo/header space
        elements.append(Spacer(1, 1 * inch))

        # Title
        elements.append(Paragraph(title, self.styles['CustomTitle']))
        elements.append(Spacer(1, 0.3 * inch))

        # Subtitle
        subtitle = "AI-Generated Research Notes"
        elements.append(Paragraph(subtitle, self.styles['Metadata']))
        elements.append(Spacer(1, 0.5 * inch))

        # Metadata
        if metadata:
            meta_items = []

            if metadata.get('doc_count'):
                meta_items.append(f"Documents Analyzed: {metadata['doc_count']}")

            if metadata.get('total_pages'):
                meta_items.append(f"Total Pages: {metadata['total_pages']}")

            if metadata.get('generated_date'):
                meta_items.append(f"Generated: {metadata['generated_date']}")
            else:
                meta_items.append(f"Generated: {datetime.now().strftime('%B %d, %Y')}")

            for item in meta_items:
                elements.append(Paragraph(item, self.styles['Metadata']))

        elements.append(Spacer(1, 1 * inch))

        # Footer
        footer_text = (
            "<i>These notes were generated by an AI Research Assistant powered by "
            "Claude Sonnet 4.5. The content represents AI-synthesized insights "
            "from the provided research documents.</i>"
        )
        elements.append(Paragraph(footer_text, self.styles['Metadata']))

        return elements

    def _create_table_of_contents(self, sections: List[Dict]) -> List:
        """Create table of contents"""
        elements = []

        elements.append(Paragraph("Table of Contents", self.styles['CustomHeading']))
        elements.append(Spacer(1, 0.2 * inch))

        toc_data = []
        for i, section in enumerate(sections, start=1):
            section_title = section.get('title', f'Section {i}')
            toc_data.append([
                Paragraph(f"{i}. {section_title}", self.styles['CustomBody']),
            ])

        if toc_data:
            toc_table = Table(toc_data, colWidths=[6 * inch])
            toc_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(toc_table)

        return elements

    def _create_content_sections(self, sections: List[Dict]) -> List:
        """Create main content sections"""
        elements = []

        for i, section in enumerate(sections):
            try:
                section_title = section.get('title', f'Section {i + 1}')
                section_content = section.get('content', '')
                citations = section.get('citations', '')
                images = section.get('images', [])

                # Section heading
                elements.append(Paragraph(section_title, self.styles['CustomHeading']))
                elements.append(Spacer(1, 0.1 * inch))

                # Section content
                if section_content:
                    # Split content into paragraphs
                    paragraphs = section_content.split('\n\n')
                    for para in paragraphs:
                        if para.strip():
                            elements.append(Paragraph(para.strip(), self.styles['CustomBody']))

                # Citations
                if citations:
                    citation_text = f"<i>{citations}</i>"
                    elements.append(Paragraph(citation_text, self.styles['Citation']))

                elements.append(Spacer(1, 0.15 * inch))

                # Images
                for img_data in images:
                    try:
                        img_path = img_data.get('path')
                        caption = img_data.get('caption', '')
                        source = img_data.get('source', '')

                        if img_path and Path(img_path).exists():
                            # Add image
                            img = RLImage(img_path, width=5 * inch, height=3 * inch, kind='proportional')
                            elements.append(img)

                            # Add caption
                            if caption or source:
                                caption_text = f"<i>{caption}</i>"
                                if source:
                                    caption_text += f" <i>[{source}]</i>"
                                elements.append(Paragraph(caption_text, self.styles['Caption']))

                            elements.append(Spacer(1, 0.2 * inch))

                    except Exception as e:
                        logger.warning(f"Failed to add image to report: {str(e)}")
                        continue

                # Add spacing between sections
                if i < len(sections) - 1:
                    elements.append(Spacer(1, 0.3 * inch))

            except Exception as e:
                logger.error(f"Error creating section {i + 1}: {str(e)}")
                continue

        return elements

    def _create_bibliography(self, bibliography: List[Dict]) -> List:
        """Create bibliography section"""
        elements = []

        elements.append(Paragraph("References", self.styles['CustomHeading']))
        elements.append(Spacer(1, 0.2 * inch))

        for i, entry in enumerate(bibliography, start=1):
            doc_name = entry.get('doc_name', 'Unknown Document')
            pages_cited = entry.get('pages_cited', [])
            citation_count = entry.get('citation_count', 0)

            # Format pages
            if pages_cited:
                if len(pages_cited) == 1:
                    pages_str = f"p.{pages_cited[0]}"
                else:
                    pages_str = f"pp.{min(pages_cited)}-{max(pages_cited)}"
            else:
                pages_str = ""

            bib_text = f"{i}. <b>{doc_name}</b>"
            if pages_str:
                bib_text += f" ({pages_str})"
            if citation_count > 1:
                bib_text += f" - Cited {citation_count} times"

            elements.append(Paragraph(bib_text, self.styles['CustomBody']))
            elements.append(Spacer(1, 0.1 * inch))

        return elements

    def create_simple_report(
        self,
        title: str,
        content_dict: Dict,
        citation_manager,
        output_filename: Optional[str] = None
    ) -> Path:
        """
        Create a simple report from analysis results

        Args:
            title: Report title
            content_dict: Dictionary with analysis results
            citation_manager: CitationManager instance
            output_filename: Optional output filename

        Returns:
            Path to generated PDF
        """
        try:
            # Prepare sections
            sections = []

            # Executive summary
            if content_dict.get('executive_summary'):
                sections.append({
                    'title': 'Executive Summary',
                    'content': content_dict['executive_summary'],
                    'citations': '',
                    'images': []
                })

            # Analysis sections
            analyses = content_dict.get('analyses', [])
            for analysis in analyses:
                query = analysis.get('query', '')
                synthesis = analysis.get('synthesis', '')
                sources = analysis.get('sources', [])

                # Get citation IDs
                citation_ids = citation_manager.add_citations_from_metadata(sources)
                citations = citation_manager.format_citation(citation_ids)

                sections.append({
                    'title': query,
                    'content': synthesis,
                    'citations': citations,
                    'images': []
                })

            # Generate bibliography
            bibliography = citation_manager.generate_bibliography()

            # Metadata
            metadata = {
                'doc_count': content_dict.get('doc_count', 0),
                'total_pages': content_dict.get('total_pages', 0),
                'generated_date': datetime.now().strftime('%B %d, %Y')
            }

            return self.generate_report(
                title=title,
                sections=sections,
                bibliography=bibliography,
                metadata=metadata,
                output_filename=output_filename
            )

        except Exception as e:
            logger.error(f"Failed to create simple report: {str(e)}")
            raise ReportGenerationError(f"Simple report creation failed: {str(e)}")
