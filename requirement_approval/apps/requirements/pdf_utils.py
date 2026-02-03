"""
PDF Generation utilities for requirements
"""
from io import BytesIO
from datetime import datetime
from django.http import FileResponse
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY


def generate_requirement_pdf(requirement):
    """
    Generate PDF for a requirement
    Returns a FileResponse object
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    # Container for PDF content
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=10,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=8,
        fontName='Helvetica-Bold',
        borderPadding=5,
        borderColor=colors.HexColor('#667eea'),
        borderWidth=1,
        borderRadius=3,
    )
    
    normal_style = styles['Normal']
    normal_style.fontSize = 10
    
    # Header
    header_data = [
        ['REQUIREMENT APPROVAL SYSTEM'],
    ]
    header_table = Table(header_data, colWidths=[7*inch])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 14),
        ('PADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Title
    elements.append(Paragraph(f'Requirement #{requirement.id}', title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Top Section - Basic Info
    top_info = [
        ['Requirement ID:', f'REQ-{requirement.id}', 'Status:', requirement.get_status_display()],
        ['Department:', requirement.get_department_display(), 'Priority:', requirement.get_priority_display()],
        ['Requested By:', requirement.requested_by.get_full_name(), 'Date:', requirement.created_date.strftime('%m/%d/%Y')],
    ]
    
    top_table = Table(top_info, colWidths=[1.2*inch, 1.8*inch, 1.2*inch, 1.8*inch])
    top_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    elements.append(top_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Item Description
    elements.append(Paragraph('Item Description', heading_style))
    elements.append(Paragraph(requirement.item_description, normal_style))
    elements.append(Spacer(1, 0.15*inch))
    
    # Justification
    elements.append(Paragraph('Justification', heading_style))
    elements.append(Paragraph(requirement.justification or 'N/A', normal_style))
    elements.append(Spacer(1, 0.15*inch))
    
    # Financial Details
    elements.append(Paragraph('Financial Details', heading_style))
    financial_data = [
        ['Estimated Cost:', f"{requirement.estimated_cost:,.2f}", 'Quantity:', str(requirement.quantity or 'N/A')],
        ['Unit Cost:', f"{requirement.estimated_cost/requirement.quantity:,.2f}" if requirement.quantity and requirement.quantity > 0 else 'N/A', 'Total Cost:', f"{(requirement.estimated_cost*requirement.quantity):,.2f}" if requirement.quantity else 'N/A'],
    ]
    
    financial_table = Table(financial_data, colWidths=[1.3*inch, 1.5*inch, 1.3*inch, 1.5*inch])
    financial_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    elements.append(financial_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Timeline Details
    elements.append(Paragraph('Timeline & Delivery', heading_style))
    timeline_data = [
        ['Duration:', requirement.duration, 'Quotation Deadline:', requirement.quotation_deadline.strftime('%m/%d/%Y')],
    ]
    
    timeline_table = Table(timeline_data, colWidths=[1.3*inch, 1.5*inch, 1.8*inch, 1.5*inch])
    timeline_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    elements.append(timeline_table)
    elements.append(Spacer(1, 0.15*inch))
    
    # Delivery Address
    elements.append(Paragraph('Delivery Address', heading_style))
    elements.append(Paragraph(requirement.delivery_address, normal_style))
    elements.append(Spacer(1, 0.15*inch))
    
    # Supporting Document
    if requirement.attachment:
        elements.append(Paragraph('Supporting Document', heading_style))
        elements.append(Paragraph(f'Attached file: {requirement.attachment.name}', normal_style))
        elements.append(Spacer(1, 0.15*inch))
    
    # Footer
    elements.append(Spacer(1, 0.3*inch))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER,
    )
    footer_text = f'Generated on {datetime.now().strftime("%m/%d/%Y %H:%M:%S")} | Requirement ID: REQ-{requirement.id}'
    elements.append(Paragraph(footer_text, footer_style))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    return buffer


def download_requirement_pdf(request, requirement):
    """
    Download requirement as PDF
    """
    buffer = generate_requirement_pdf(requirement)
    
    response = FileResponse(buffer, as_attachment=True, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Requirement_{requirement.id}.pdf"'
    
    return response
