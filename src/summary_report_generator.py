"""
Summary Documentation Generator
Creates comprehensive summary documents with images, detailed citations, and visual references
"""

from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib.colors import HexColor
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
    PageBreak, Table, TableStyle, KeepTogether, Flowable
)
from reportlab.pdfgen import canvas as pdf_canvas

from config.settings import OUTPUT_DIR
from utils.logger import get_logger
from utils.exceptions import ReportGenerationError

logger = get_logger(__name__)


class PageNumCanvas(pdf_canvas.Canvas):
    """Custom canvas with page numbers and footer"""

    def __init__(self, *args, **kwargs):
        pdf_canvas.Canvas.__init__(self, *args, **kwargs)
        self.pages = []

    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self.pages)
        for page_num, page in enumerate(self.pages, start=1):
            self.__dict__.update(page)
            self.draw_page_elements(page_num, page_count)
            pdf_canvas.Canvas.showPage(self)
        pdf_canvas.Canvas.save(self)

    def draw_page_elements(self, page_num, page_count):
        """Draw page number and footer"""
        # Page number
        self.setFont("Helvetica", 9)
        self.setFillColor(HexColor("#7f8c8d"))
        self.drawRightString(
            7.5 * inch,
            0.5 * inch,
            f"Page {page_num} of {page_count}"
        )

        # Footer line
        self.setStrokeColor(HexColor("#ecf0f1"))
        self.setLineWidth(0.5)
        self.line(0.75 * inch, 0.6 * inch, 7.75 * inch, 0.6 * inch)


class SummaryReportGenerator:
    """
    Generates comprehensive summary documentation with:
    - Detailed summaries
    - Inline citations with document/page references
    - Embedded images from source PDFs
    - Visual document indicators
    - Clean, readable format
    """

    def __init__(self):
        """Initialize summary report generator"""
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()
        logger.info("Summary report generator initialized")

    def _create_custom_styles(self):
        """Create custom paragraph styles for summary documentation"""

        # Title style
        self.styles.add(ParagraphStyle(
            name='SummaryTitle',
            parent=self.styles['Heading1'],
            fontSize=28,
            textColor=HexColor('#2c3e50'),
            spaceAfter=20,
            spaceBefore=0,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            leading=34
        ))

        # Subtitle
        self.styles.add(ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=HexColor('#7f8c8d'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Oblique'
        ))

        # Section heading
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=18,
            textColor=HexColor('#2c3e50'),
            spaceAfter=15,
            spaceBefore=25,
            fontName='Helvetica-Bold',
            borderWidth=0,
            borderColor=HexColor('#3498db'),
            borderPadding=5,
            leftIndent=0,
            leading=22
        ))

        # Subsection heading
        self.styles.add(ParagraphStyle(
            name='SubsectionHeading',
            parent=self.styles['Heading3'],
            fontSize=14,
            textColor=HexColor('#34495e'),
            spaceAfter=10,
            spaceBefore=15,
            fontName='Helvetica-Bold',
            leading=18
        ))

        # Body text
        self.styles.add(ParagraphStyle(
            name='SummaryBody',
            parent=self.styles['BodyText'],
            fontSize=11,
            alignment=TA_JUSTIFY,
            spaceAfter=12,
            leading=16,
            textColor=HexColor('#2c3e50')
        ))

        # Citation style - more prominent
        self.styles.add(ParagraphStyle(
            name='InlineCitation',
            parent=self.styles['BodyText'],
            fontSize=9,
            textColor=HexColor('#3498db'),
            leftIndent=25,
            rightIndent=10,
            spaceAfter=8,
            spaceBefore=2,
            fontName='Helvetica-Oblique',
            leading=12,
            backColor=HexColor('#ecf0f1')
        ))

        # Document reference badge
        self.styles.add(ParagraphStyle(
            name='DocBadge',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.white,
            backColor=HexColor('#3498db'),
            fontName='Helvetica-Bold',
            leftIndent=5,
            rightIndent=5,
            spaceAfter=5
        ))

        # Image caption
        self.styles.add(ParagraphStyle(
            name='ImageCaption',
            parent=self.styles['BodyText'],
            fontSize=10,
            textColor=HexColor('#5d6d7e'),
            alignment=TA_CENTER,
            spaceAfter=15,
            spaceBefore=8,
            fontName='Helvetica-Oblique',
            leading=13
        ))

        # Key insight box
        self.styles.add(ParagraphStyle(
            name='KeyInsight',
            parent=self.styles['BodyText'],
            fontSize=11,
            textColor=HexColor('#27ae60'),
            leftIndent=20,
            rightIndent=20,
            spaceAfter=15,
            spaceBefore=10,
            fontName='Helvetica-Bold',
            borderWidth=2,
            borderColor=HexColor('#27ae60'),
            borderPadding=10,
            backColor=HexColor('#e8f8f5')
        ))

        # Highlighted main point style (yellow highlight)
        self.styles.add(ParagraphStyle(
            name='HighlightedPoint',
            parent=self.styles['BodyText'],
            fontSize=11,
            textColor=HexColor('#2c3e50'),
            leftIndent=15,
            rightIndent=15,
            spaceAfter=12,
            spaceBefore=8,
            fontName='Helvetica-Bold',
            backColor=HexColor('#fff3cd'),  # Yellow highlight
            borderWidth=1,
            borderColor=HexColor('#ffc107'),
            borderPadding=8,
            leading=16
        ))

    def _create_title_page(self, title: str, metadata: Dict) -> List:
        """Create an informative title page"""
        elements = []

        elements.append(Spacer(1, 1.5 * inch))

        # Main title
        elements.append(Paragraph(title, self.styles['SummaryTitle']))
        elements.append(Spacer(1, 0.3 * inch))

        # Subtitle
        subtitle = "Comprehensive Research Notes"
        elements.append(Paragraph(subtitle, self.styles['Subtitle']))
        elements.append(Spacer(1, 0.8 * inch))

        # Metadata box
        meta_data = [
            ["Documents Analyzed:", str(metadata.get('doc_count', 0))],
            ["Total Pages:", str(metadata.get('total_pages', 0))],
            ["Generated:", datetime.now().strftime('%B %d, %Y at %I:%M %p')]
        ]

        meta_table = Table(meta_data, colWidths=[2.5 * inch, 3 * inch])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), HexColor('#2c3e50')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#bdc3c7')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
        ]))

        elements.append(meta_table)
        elements.append(Spacer(1, 1 * inch))

        # Description
        description = (
            "<i>This document provides comprehensive research notes from the analyzed papers. "
            "Each section includes detailed theoretical insights with specific citations showing the exact source "
            "document, page number, and section. The notes focus on deep understanding of concepts and methodologies.</i>"
        )
        elements.append(Paragraph(description, self.styles['SummaryBody']))

        return elements

    def _create_document_index(self, documents: List[Dict]) -> List:
        """Create an index of all analyzed documents"""
        elements = []

        elements.append(Paragraph("📚 Documents Analyzed", self.styles['SectionHeading']))
        elements.append(Spacer(1, 0.2 * inch))

        for i, doc in enumerate(documents, 1):
            doc_name = doc.get('doc_name', f'Document {i}')
            metadata = doc.get('metadata', {})
            page_count = len(doc.get('pages', []))

            # Document entry
            doc_text = f"<b>[Doc {i}]</b> {doc_name}"
            elements.append(Paragraph(doc_text, self.styles['SummaryBody']))

            # Details
            details = f"&nbsp;&nbsp;&nbsp;&nbsp;• Pages: {page_count}"
            if metadata.get('author'):
                details += f" | Author: {metadata.get('author')}"

            elements.append(Paragraph(details, self.styles['Normal']))
            elements.append(Spacer(1, 0.15 * inch))

        return elements

    def _is_main_point(self, text: str) -> bool:
        """
        Detect if a sentence/paragraph is a main point that should be highlighted

        Criteria:
        - Starts with bullet points (-, •, *, →)
        - Contains keywords like "key", "main", "important", "critical", "significant"
        - Starts with numbered points (1., 2., etc.)
        - Contains "finding", "result", "conclusion", "shows that", "demonstrates"
        """
        text_lower = text.lower().strip()

        # Check for bullet points
        if text_lower.startswith(('-', '•', '*', '→', '▪')):
            return True

        # Check for numbered points
        if len(text_lower) > 2 and text_lower[0].isdigit() and text_lower[1] in '.):':
            return True

        # Check for key indicator keywords at the start
        start_keywords = [
            'key', 'main', 'important', 'critical', 'significant',
            'notably', 'primarily', 'essentially', 'fundamentally'
        ]
        if any(text_lower.startswith(kw) for kw in start_keywords):
            return True

        # Check for result/conclusion keywords
        result_keywords = [
            'finding', 'result', 'conclusion', 'shows that', 'demonstrates',
            'reveals', 'indicates', 'suggests', 'proves', 'establishes'
        ]
        if any(kw in text_lower for kw in result_keywords):
            return True

        return False

    def _format_citation_badge(self, doc_name: str, page: int, section: str = None) -> str:
        """Format a citation as a colored badge"""
        citation = f"📄 {doc_name}, p.{page}"
        if section:
            citation += f", §{section}"
        return f'<font color="#3498db" size="9"><b>[{citation}]</b></font>'

    def _add_image_with_citation(self, image_path: Path, caption: str, source_ref: str) -> List:
        """Add an image with caption and source reference"""
        elements = []

        try:
            if image_path and image_path.exists():
                # Add some spacing before image
                elements.append(Spacer(1, 0.2 * inch))

                # Add the image
                img = RLImage(str(image_path), width=5.5 * inch, height=4 * inch, kind='proportional')
                elements.append(img)

                # Add caption with source
                caption_text = f"<i>{caption}</i><br/><font color='#3498db'><b>{source_ref}</b></font>"
                elements.append(Paragraph(caption_text, self.styles['ImageCaption']))

                elements.append(Spacer(1, 0.2 * inch))

        except Exception as e:
            logger.warning(f"Could not add image: {str(e)}")

        return elements

    def generate_summary_report(
        self,
        title: str,
        summary_sections: List[Dict],
        documents_data: List[Dict],
        citation_manager,
        output_filename: Optional[str] = None
    ) -> Path:
        """
        Generate comprehensive summary documentation

        Args:
            title: Report title
            summary_sections: List of summary section dictionaries
            documents_data: Original PDF data with images
            citation_manager: CitationManager instance
            output_filename: Optional output filename

        Returns:
            Path to generated PDF
        """
        try:
            logger.info(f"Generating summary documentation: {title}")

            # Create output filename
            if not output_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_'))
                safe_title = safe_title.replace(' ', '_')[:50]
                output_filename = f"Summary_{safe_title}_{timestamp}.pdf"

            output_path = OUTPUT_DIR / output_filename

            # Create PDF document
            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=letter,
                rightMargin=0.75 * inch,
                leftMargin=0.75 * inch,
                topMargin=0.75 * inch,
                bottomMargin=0.75 * inch
            )

            # Build story
            story = []

            # Create metadata
            metadata = {
                'doc_count': len(documents_data),
                'total_pages': sum(len(d.get('pages', [])) for d in documents_data),
                'total_images': sum(d.get('total_images', 0) for d in documents_data)
            }

            # Title page
            story.extend(self._create_title_page(title, metadata))

            # Document index
            story.append(PageBreak())
            story.extend(self._create_document_index(documents_data))

            # Summary sections
            story.append(PageBreak())
            story.extend(self._create_summary_sections(summary_sections, documents_data, citation_manager))

            # Build PDF
            doc.build(story, canvasmaker=PageNumCanvas)

            logger.info(f"Summary documentation generated: {output_path.name}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate summary documentation: {str(e)}")
            raise ReportGenerationError(f"Summary generation failed: {str(e)}")

    def _create_summary_sections(
        self,
        sections: List[Dict],
        documents_data: List[Dict],
        citation_manager
    ) -> List:
        """Create detailed summary sections with citations and images"""
        elements = []

        for i, section in enumerate(sections):
            try:
                section_title = section.get('title', f'Section {i + 1}')
                content = section.get('content', '')
                sources = section.get('sources', [])
                related_images = section.get('images', [])

                # Section heading
                elements.append(Paragraph(f"📌 {section_title}", self.styles['SectionHeading']))
                elements.append(Spacer(1, 0.15 * inch))

                # Split content into paragraphs
                paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

                for para_idx, para in enumerate(paragraphs):
                    if para:
                        # Determine if this is a main point that should be highlighted
                        if self._is_main_point(para):
                            # Add highlighted paragraph for main points
                            elements.append(Paragraph(f"💡 {para}", self.styles['HighlightedPoint']))
                        else:
                            # Add normal paragraph
                            elements.append(Paragraph(para, self.styles['SummaryBody']))

                        # Add citations for this paragraph
                        if sources:
                            citation_ids = citation_manager.add_citations_from_metadata(sources[:3])  # Top 3 sources
                            citations_text = citation_manager.format_citation(citation_ids, style="inline")

                            # Add detailed source references
                            source_details = []
                            for source in sources[:3]:
                                doc_name = source.get('doc_name', 'Unknown')
                                page = source.get('page', '?')
                                section_name = source.get('section', '')
                                detail = f"→ {doc_name}, Page {page}"
                                if section_name:
                                    detail += f", Section: {section_name}"
                                source_details.append(detail)

                            references_text = "<br/>".join(source_details)
                            elements.append(Paragraph(
                                f'<font size="9"><i>Sources: {citations_text}</i><br/>{references_text}</font>',
                                self.styles['InlineCitation']
                            ))

                        elements.append(Spacer(1, 0.1 * inch))

                # Add related images
                for img_data in related_images[:3]:  # Limit to 3 images per section
                    img_path = img_data.get('path')
                    if img_path:
                        caption = img_data.get('caption', 'Figure from research document')
                        source_ref = f"Source: {img_data.get('doc_name', 'Unknown')}, Page {img_data.get('page', '?')}"
                        elements.extend(self._add_image_with_citation(Path(img_path), caption, source_ref))

                # Add spacing between sections
                if i < len(sections) - 1:
                    elements.append(Spacer(1, 0.3 * inch))

            except Exception as e:
                logger.error(f"Error creating section {i + 1}: {str(e)}")
                continue

        return elements
