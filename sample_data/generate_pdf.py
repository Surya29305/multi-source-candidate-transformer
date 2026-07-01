import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def make_pdf():
    pdf_path = "sample_data/resume_candidate.pdf"
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Normal'],
        fontSize=11,
        leading=14,
        spaceAfter=12
    )
    heading_style = ParagraphStyle(
        'HeadingStyle',
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        spaceBefore=10,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        spaceAfter=4
    )
    
    story = []
    story.append(Paragraph("Ravi Krishnamurthy", title_style))
    story.append(Paragraph("Backend Software Engineer<br/>San Francisco, CA<br/>United States<br/>ravi.krishnamurthy@stripe.com<br/>+1 415 867 5309<br/>github.com/ravikrishnamurthy", subtitle_style))
    
    story.append(Paragraph("Summary", heading_style))
    story.append(Paragraph("Backend engineer specializing in distributed systems, high-performance Python services, and containerized deployments.", body_style))
    
    story.append(Paragraph("Experience", heading_style))
    story.append(Paragraph("Stripe, Backend Software Engineer", body_style))
    story.append(Paragraph("March 2022 - Present", body_style))
    story.append(Paragraph("San Francisco, CA", body_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Uber, Software Engineer (Backend)", body_style))
    story.append(Paragraph("July 2019 - February 2022", body_style))
    story.append(Paragraph("San Francisco, CA", body_style))
    
    story.append(Paragraph("Education", heading_style))
    story.append(Paragraph("University of California, Berkeley", body_style))
    story.append(Paragraph("Bachelor of Science, Computer Science", body_style))
    story.append(Paragraph("2015 - 2019", body_style))
    
    story.append(Paragraph("Skills", heading_style))
    story.append(Paragraph("Python, Docker, Git, AWS, Kubernetes", body_style))
    
    story.append(Paragraph("Certifications", heading_style))
    story.append(Paragraph("AWS Certified Solutions Architect (2023)", body_style))
    story.append(Paragraph("Certified Kubernetes Administrator (2024)", body_style))
    
    doc.build(story)

if __name__ == '__main__':
    make_pdf()
