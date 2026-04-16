"""
PDF audit report generation.
Exports accessibility audit data to professional PDF format.
"""

import io
import logging
from datetime import datetime
from typing import List, Optional

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from src.models import AuditReport, AccessibilityScore
from src.utils import get_logger

logger = get_logger(__name__)


class PDFReportGenerator:
    """Generate professional PDF audit reports."""
    
    def __init__(self, page_size=letter):
        """
        Initialize PDF generator.
        
        Args:
            page_size: Page size (letter or A4)
        """
        self.page_size = page_size
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
        ))
        
        # Heading style
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold',
        ))
        
        # Normal text
        self.styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_LEFT,
        ))
    
    def _create_title_page(self, report: AuditReport) -> List:
        """Create title page elements."""
        elements = []
        
        # Title
        elements.append(Spacer(1, 1 * inch))
        elements.append(Paragraph(
            "Accessibility Audit Report",
            self.styles['CustomTitle']
        ))
        
        # Subtitle
        elements.append(Paragraph(
            f"Urban Public Transport System",
            self.styles['Heading2']
        ))
        
        elements.append(Spacer(1, 0.5 * inch))
        
        # City and date
        elements.append(Paragraph(
            f"<b>City:</b> {report.city}",
            self.styles['CustomNormal']
        ))
        elements.append(Paragraph(
            f"<b>Report Date:</b> {report.generated_at.strftime('%B %d, %Y')}",
            self.styles['CustomNormal']
        ))
        elements.append(Paragraph(
            f"<b>Report ID:</b> {report.report_id}",
            self.styles['CustomNormal']
        ))
        elements.append(Paragraph(
            f"<b>Data Source:</b> {report.data_source.upper()}",
            self.styles['CustomNormal']
        ))
        if report.image_detector_mode:
            elements.append(Paragraph(
                f"<b>Image Detector Mode:</b> {report.image_detector_mode}",
                self.styles['CustomNormal']
            ))
        
        elements.append(Spacer(1, 0.5 * inch))
        
        # Executive summary box
        elements.append(Paragraph(
            "<b>Executive Summary</b>",
            self.styles['CustomHeading']
        ))
        
        summary_text = f"""
        This report presents a comprehensive accessibility audit of the public transport network
        in {report.city}. The audit analyzed <b>{report.total_stops_audited} transit stops</b>
        and <b>{report.total_grievances_analyzed} citizen complaints</b>, achieving
        <b>{report.coverage_percent:.1f}%</b> network coverage.
        <br/><br/>
        <b>Key Metrics:</b><br/>
        • Average Gap Score: {report.avg_gap_score:.1f}/100<br/>
        • Critical Priority Stops: {report.stops_by_priority['CRITICAL']}<br/>
        • High Priority Stops: {report.stops_by_priority['HIGH']}<br/>
        • Analysis Time: {report.generation_time_seconds}s
        """
        
        elements.append(Paragraph(summary_text, self.styles['CustomNormal']))
        elements.append(PageBreak())
        
        return elements
    
    def _create_key_findings_section(self, report: AuditReport) -> List:
        """Create key findings section."""
        elements = []
        
        elements.append(Paragraph("Key Findings", self.styles['CustomHeading']))
        elements.append(Spacer(1, 0.2 * inch))
        
        for i, finding in enumerate(report.key_findings, 1):
            elements.append(Paragraph(
                f"{i}. {finding}",
                self.styles['CustomNormal']
            ))
            elements.append(Spacer(1, 0.1 * inch))
        
        elements.append(Spacer(1, 0.3 * inch))
        return elements

    def _create_image_summary_section(self, report: AuditReport) -> List:
        """Create a compact summary of analyzed images."""
        elements = []

        if not report.image_analysis_enabled or not report.image_findings_summary:
            return elements

        elements.append(Paragraph("Image-Based Accessibility Findings", self.styles['CustomHeading']))
        elements.append(Spacer(1, 0.1 * inch))

        table_data = [['Image', 'Stop ID', 'Signal', 'Confidence']]
        for summary in report.image_findings_summary[:10]:
            table_data.append([
                summary.image_name[:28],
                summary.stop_id or 'N/A',
                summary.overall_signal or 'unknown',
                f"{summary.overall_confidence:.2f}",
            ])

        table = Table(table_data, colWidths=[2.3*inch, 1.1*inch, 1.4*inch, 1.0*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.3 * inch))
        return elements

    def _create_evaluation_section(self, report: AuditReport) -> List:
        """Create evaluation metrics section (precision/recall/F1)."""
        elements = []

        if not report.evaluation_metrics:
            return elements

        elements.append(Paragraph("Model Evaluation Metrics", self.styles['CustomHeading']))
        elements.append(Spacer(1, 0.1 * inch))

        table_data = [
            ["Metric", "Value"],
            ["Precision", f"{report.evaluation_metrics.get('precision', 0):.4f}"],
            ["Recall", f"{report.evaluation_metrics.get('recall', 0):.4f}"],
            ["F1 Score", f"{report.evaluation_metrics.get('f1_score', 0):.4f}"],
            ["Evaluated Stops", f"{int(report.evaluation_metrics.get('evaluated_stops', 0))}"],
        ]

        table = Table(table_data, colWidths=[2.0*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.3 * inch))
        return elements
    
    def _create_priority_distribution_table(self, report: AuditReport) -> List:
        """Create priority distribution table."""
        elements = []
        
        elements.append(Paragraph("Priority Distribution", self.styles['CustomHeading']))
        elements.append(Spacer(1, 0.1 * inch))
        
        # Create table data
        table_data = [
            ['Priority Level', 'Count', 'Percentage'],
            ['CRITICAL', str(report.stops_by_priority['CRITICAL']),
             f"{(report.stops_by_priority['CRITICAL'] / report.total_stops_audited * 100):.1f}%"],
            ['HIGH', str(report.stops_by_priority['HIGH']),
             f"{(report.stops_by_priority['HIGH'] / report.total_stops_audited * 100):.1f}%"],
            ['MEDIUM', str(report.stops_by_priority['MEDIUM']),
             f"{(report.stops_by_priority['MEDIUM'] / report.total_stops_audited * 100):.1f}%"],
            ['LOW', str(report.stops_by_priority['LOW']),
             f"{(report.stops_by_priority['LOW'] / report.total_stops_audited * 100):.1f}%"],
        ]
        
        table = Table(table_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3 * inch))
        
        return elements
    
    def _create_grievance_themes_section(self, report: AuditReport) -> List:
        """Create grievance themes section."""
        elements = []
        
        elements.append(Paragraph("Grievance Themes Analysis", self.styles['CustomHeading']))
        elements.append(Spacer(1, 0.1 * inch))
        
        if not report.grievance_themes:
            elements.append(Paragraph("No grievance themes identified.", self.styles['CustomNormal']))
            return elements
        
        # Create table
        table_data = [['Theme', 'Count', 'Top Keywords']]
        
        for cluster in report.grievance_themes[:10]:  # Top 10 themes
            keywords = ', '.join(cluster.top_keywords[:3]) if cluster.top_keywords else 'N/A'
            table_data.append([
                cluster.theme[:30],
                str(cluster.count),
                keywords[:40]
            ])
        
        table = Table(table_data, colWidths=[2*inch, 1*inch, 3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3 * inch))
        
        return elements
    
    def _create_top_priority_stops_section(self, report: AuditReport) -> List:
        """Create top priority stops section."""
        elements = []
        
        elements.append(PageBreak())
        elements.append(Paragraph("Top Priority Stops for Intervention", self.styles['CustomHeading']))
        elements.append(Spacer(1, 0.1 * inch))
        
        # Create detailed list
        for i, stop in enumerate(report.top_priority_stops[:10], 1):
            stop_info = f"""
            <b>{i}. {stop.stop_name}</b> (Gap Score: {stop.gap_score}/100, Priority: {stop.priority_level.value})<br/>
            Location: ({stop.latitude:.4f}, {stop.longitude:.4f})<br/>
            Grievances: {stop.grievance_count} | Top Issues: {', '.join(stop.top_themes[:2])}<br/>
            Estimated Cost: {stop.remediation_cost_estimate}<br/>
            """
            
            elements.append(Paragraph(stop_info, self.styles['CustomNormal']))
            
            # Recommendations
            if stop.recommendations:
                rec_text = "<b>Recommendations:</b><br/>"
                for rec in stop.recommendations[:2]:
                    rec_text += f"• {rec}<br/>"
                elements.append(Paragraph(rec_text, self.styles['CustomNormal']))
            
            elements.append(Spacer(1, 0.15 * inch))
        
        return elements
    
    def _create_recommendations_section(self, report: AuditReport) -> List:
        """Create strategic recommendations section."""
        elements = []
        
        elements.append(PageBreak())
        elements.append(Paragraph("Strategic Recommendations", self.styles['CustomHeading']))
        elements.append(Spacer(1, 0.1 * inch))
        
        for i, rec in enumerate(report.recommendations, 1):
            elements.append(Paragraph(
                f"{i}. {rec}",
                self.styles['CustomNormal']
            ))
            elements.append(Spacer(1, 0.1 * inch))
        
        return elements
    
    def _create_footer_section(self, report: AuditReport) -> List:
        """Create footer section."""
        elements = []
        
        elements.append(Spacer(1, 0.5 * inch))
        elements.append(Paragraph(
            f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ParagraphStyle(name='Footer', fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
        ))
        
        return elements
    
    def generate(self, report: AuditReport, output_path: Optional[str] = None) -> bytes:
        """
        Generate PDF report.
        
        Args:
            report: AuditReport object
            output_path: Path to save PDF (if None, returns bytes)
        
        Returns:
            PDF bytes if output_path is None, else None
        """
        logger.info(f"Generating PDF report: {report.report_id}")
        
        # Create PDF in memory or file
        if output_path is None:
            pdf_buffer = io.BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=self.page_size)
        else:
            doc = SimpleDocTemplate(output_path, pagesize=self.page_size)
        
        # Build elements
        elements = []
        
        # Title page
        elements.extend(self._create_title_page(report))
        
        # Key findings
        elements.extend(self._create_key_findings_section(report))
        
        # Priority distribution
        elements.extend(self._create_priority_distribution_table(report))
        
        # Grievance themes
        elements.extend(self._create_grievance_themes_section(report))

        # Image findings
        elements.extend(self._create_image_summary_section(report))

        # Evaluation metrics
        elements.extend(self._create_evaluation_section(report))
        
        # Top priority stops
        elements.extend(self._create_top_priority_stops_section(report))
        
        # Recommendations
        elements.extend(self._create_recommendations_section(report))
        
        # Footer
        elements.extend(self._create_footer_section(report))
        
        # Build PDF
        doc.build(elements)
        
        if output_path is None:
            pdf_bytes = pdf_buffer.getvalue()
            logger.info(f"PDF generated ({len(pdf_bytes)} bytes)")
            return pdf_bytes
        else:
            logger.info(f"PDF saved to {output_path}")
            return None


def generate_pdf_report(report: AuditReport, output_path: Optional[str] = None) -> bytes:
    """
    Convenience function to generate PDF report.
    
    Args:
        report: AuditReport object
        output_path: Output file path (if None, returns bytes)
    
    Returns:
        PDF bytes if output_path is None, else None
    """
    generator = PDFReportGenerator()
    return generator.generate(report, output_path)
