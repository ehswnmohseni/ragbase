from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageTemplate, BaseDocTemplate, Frame
from ragbase.scrapper import fetch_top_wikipedia_results
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import HexColor
import os
import base64
from datetime import datetime
from typing import Union
import streamlit as st

class BorderCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        self.border_color = kwargs.pop('border_color', HexColor("#2C3E50"))
        self.border_width = kwargs.pop('border_width', 2)
        super().__init__(*args, **kwargs)

    def showPage(self):
        self.draw_border()
        super().showPage()

    def draw_border(self):
        width, height = A4
        self.setStrokeColor(self.border_color)
        self.setLineWidth(self.border_width)
        margin = 15
        self.rect(margin, margin, width - 2*margin, height - 2*margin)

def display_pdf_demo(pdf_path):
    try:
        with open(pdf_path, "rb") as pdf_file:
            base64_pdf = base64.b64encode(pdf_file.read()).decode('utf-8')
        
        pdf_display = f'''
        <div style="border: 2px solid #e0e0e0; border-radius: 10px; padding: 10px; background-color: #f9f9f9;">
            <h4 style="margin-top: 0; color: #333;">📄 PDF Preview - First Page</h4>
            <iframe 
                src="data:application/pdf;base64,{base64_pdf}" 
                width="100%" 
                height="500" 
                style="border: 1px solid #ddd; border-radius: 5px;"
                type="application/pdf">
            </iframe>
            <div style="margin-top: 10px; font-size: 0.9em; color: #666;">
                <strong>File:</strong> {os.path.basename(pdf_path)} | 
                <strong>Size:</strong> {os.path.getsize(pdf_path) // 1024} KB
            </div>
        </div>
        '''
        st.markdown(pdf_display, unsafe_allow_html=True)
        
        with open(pdf_path, "rb") as file:
            st.download_button(
                label="📥 Download Full PDF",
                data=file,
                file_name=os.path.basename(pdf_path),
                mime="application/pdf",
                use_container_width=True
            )
            
    except Exception as e:
        st.error(f"Error displaying PDF demo: {e}")


def save_summary_as_pdf(
    title: str, 
    content: Union[str, list], 
    output_dir: str = "documents",
    template_style: str = "modern",
    content_file: str = None,
    logo_path: str = "images/logo.png",
    add_border: bool = True,
    border_color: str = "#2C3E50",
    border_width: int = 2,
    show_preview: bool = True
):
    
    os.makedirs(output_dir, exist_ok=True)
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_title = safe_title.replace(" ", "_")
    pdf_path = os.path.join(output_dir, f"{safe_title}.pdf")

    if content_file and os.path.exists(content_file):
        with open(content_file, 'r', encoding='utf-8') as file:
            content = file.read()

    if isinstance(content, str):
        content = content.split("\n")

    template_styles = {
        "professional": {
            "title_color": "#2C3E50",
            "text_color": "#34495E",
            "accent_color": "#2980B9",
            "font_name": "Helvetica",
            "border_color": "#2C3E50"
        },
        "modern": {
            "title_color": "#27AE60",
            "text_color": "#2C3E50",
            "accent_color": "#E74C3C",
            "font_name": "Helvetica",
            "border_color": "#27AE60"
        },
        "elegant": {
            "title_color": "#8E44AD",
            "text_color": "#2C3E50",
            "accent_color": "#16A085",
            "font_name": "Times-Roman",
            "border_color": "#8E44AD"
        }
    }

    style_config = template_styles.get(template_style, template_styles["modern"])
    
    if border_color == "#2C3E50":
        border_color = style_config["border_color"]

    if add_border:
        doc = BaseDocTemplate(
            pdf_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        frame = Frame(
            doc.leftMargin, 
            doc.bottomMargin, 
            doc.width, 
            doc.height,
            leftPadding=0,
            rightPadding=0,
            bottomPadding=0,
            topPadding=0,
            id='normal'
        )
        
        def add_border_canvas(canvas, doc):
            border_canvas = BorderCanvas(
                canvas._filename, 
                canvas._pagesize,
                border_color=HexColor(border_color),
                border_width=border_width
            )
            return border_canvas

        template = PageTemplate(
            id='WithBorder', 
            frames=frame,
            onPage=add_border_canvas
        )
        
        doc.addPageTemplates([template])
    else:
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=f"{style_config['font_name']}-Bold",
        fontSize=18,
        textColor=HexColor(style_config['title_color']),
        spaceAfter=30,
        alignment=1
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontName=style_config['font_name'],
        fontSize=10,
        textColor=HexColor(style_config['accent_color']),
        alignment=1
    )

    content_style = ParagraphStyle(
        'CustomContent',
        parent=styles['BodyText'],
        fontName=style_config['font_name'],
        fontSize=11,
        textColor=HexColor(style_config['text_color']),
        spaceAfter=12,
        leading=14
    )

    story = []

    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=1.5*inch, height=1.5*inch)
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 20))
        except:
            pass

    story.append(Paragraph(title, title_style))
    
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    story.append(Paragraph(f"Generated on: {date_str}", subtitle_style))
    story.append(Spacer(1, 30))

    for line in content:
        if line.strip():
            story.append(Paragraph(line.strip(), content_style))
        else:
            story.append(Spacer(1, 12))

    doc.build(story)
    
    if show_preview and st is not None:
        try:
            st.subheader("🎯 Generated PDF Preview")
            with st.expander("📋 Click to view the generated PDF", expanded=True):
                display_pdf_demo(pdf_path)
        except Exception as e:
            print(f"Error displaying PDF preview: {e}")
    
    return pdf_path

def read_content_from_file(file_path: str) -> list:
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.readlines()
        return [line.strip() for line in content if line.strip()]
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return []
    
def save_wikipedia_results_to_pdf(user_text: str, top_n: int = 3, logo_path="images/logo.png", show_preview: bool = True):
    items = fetch_top_wikipedia_results(user_text, n=top_n, sentences=10)
    if not items:
        print("No Wikipedia results found.")
        return None

    pdf_content_lines = []
    for i, item in enumerate(items, start=1):
        pdf_content_lines.append(f"{i}. {item['title']}")
        pdf_content_lines.append(item['source_url'])
        pdf_content_lines.append("")
        pdf_content_lines.extend(item['content'].split("\n"))
        pdf_content_lines.append("\n\n")

    pdf_path = save_summary_as_pdf(
        title=f"{user_text}",
        content=pdf_content_lines,
        logo_path=logo_path,
        show_preview=show_preview
    )

    return pdf_path