import os
import time
import pandas as pd
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import PageTemplate, Frame
from reportlab.pdfgen import canvas
from csv_to_polyline import data_to_polyline
from cal_ch_offset import calculate_chainage_offset


def format_feature_name(features):
    """ Converts feature pairs into formatted string, ensuring proper structure. """
    feature_list = []

    for i in range(0, len(features), 2):
        feature_key = features[i]
        feature_value = features[i + 1] if i + 1 < len(features) else "NA"

        # Skip "NA=NA" pairs
        if feature_key == "NA" and feature_value == "NA":
            continue

        formatted_feature = f"{feature_key}={feature_value}"
        feature_list.append(formatted_feature)

    # Remove empty "/" cases
    feature_name = "/".join(feature_list).strip("/")

    return feature_name if feature_name else "NA"  # Ensure empty values return "NA"


def extract_value(feature_value):
    """ Extracts the part after ':' if exists, else returns original value. """
    if pd.isna(feature_value) or feature_value in ["nan", "NaN", "NAN"]:  # Replace missing values
        return "NA"
    return feature_value.split(":")[-1].strip() if ":" in feature_value else feature_value


# Custom canvas for header and footer
class MyCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        self.report_info = kwargs.pop('report_info', {})
        canvas.Canvas.__init__(self, *args, **kwargs)
        self.pages = []
        self.width, self.height = landscape(A4)

    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self.pages)
        for page in self.pages:
            self.__dict__.update(page)
            self.draw_header_footer(page_count)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_header_footer(self, page_count):
        page = self._pageNumber
        self.saveState()

        # Background for header
        self.setFillColor(colors.HexColor("#f9f9f9"))
        self.rect(20, self.height - 120, self.width - 40, 80, fill=1, stroke=0)

        # Decorative element
        self.setFillColor(colors.HexColor("#003366"))
        self.rect(20, self.height - 120, 10, 80, fill=1, stroke=0)

        # Company Name
        self.setFillColor(colors.HexColor("#003366"))
        self.setFont("Helvetica-Bold", 18)
        self.drawString(40, self.height - 40, "Navvis Geomatics")

        # Title
        self.setFont("Helvetica-Bold", 22)
        self.drawString(40, self.height - 70, "Point Report")

        # Calculate column positions (divide usable width into 5 equal columns)
        left_margin = 40
        col_width = (self.width - (left_margin * 2)) / 5

        # Define columns
        col1 = left_margin
        col2 = left_margin + col_width
        col3 = left_margin + (col_width * 2)
        col4 = left_margin + (col_width * 3)
        col5 = left_margin + (col_width * 4)

        # Base y position
        y_pos = self.height - 100

        # Second column - Project info
        self.setFont("Helvetica-Bold", 11)
        self.setFillColor(colors.HexColor("#003366"))
        self.drawString(col2, y_pos + 15, "Project Information")
        self.setFillColor(colors.black)
        self.setFont("Helvetica", 10)
        self.drawString(col2, y_pos, f"Project: {self.report_info.get('Project', '')}")
        self.drawString(col2, y_pos - 15, f"Spread: {self.report_info.get('Spread', '')}")
        self.drawString(col2, y_pos - 30, f"File: {self.report_info.get('File', '')}")

        # Third column - Base point info
        self.setFont("Helvetica-Bold", 11)
        self.setFillColor(colors.HexColor("#003366"))
        self.drawString(col3, y_pos + 15, "Base Point Information")
        self.setFillColor(colors.black)
        self.setFont("Helvetica", 10)
        self.drawString(col3, y_pos, f"Base Point: {self.report_info.get('Base Point', '')}")
        self.drawString(col3, y_pos - 15, f"Point Number:")

        # Fourth column - Control check
        self.setFont("Helvetica-Bold", 11)
        self.setFillColor(colors.HexColor("#003366"))
        self.drawString(col4, y_pos + 15, "Control Check")
        self.setFillColor(colors.black)
        self.setFont("Helvetica", 10)
        self.drawString(col4, y_pos, f"Control check:")
        self.drawString(col4, y_pos - 15, f"Point Number: 5960890")

        # Fifth column - Additional info
        self.setFont("Helvetica-Bold", 11)
        self.setFillColor(colors.HexColor("#003366"))
        self.drawString(col5, y_pos + 15, "Code Information")
        self.setFillColor(colors.black)
        self.setFont("Helvetica", 10)
        self.drawString(col5, y_pos, f"{self.report_info.get('Point Number', '214 codes')}")
        self.drawString(col5, y_pos - 15, f"{self.report_info.get('Control check', '0 Not entered')}")
        self.drawString(col5, y_pos - 30, f"Score: {self.report_info.get('Score', '100.00%')}")

        # Add a line below the header
        self.setStrokeColor(colors.HexColor("#003366"))
        self.setLineWidth(2)
        self.line(40, y_pos - 45, self.width - 40, y_pos - 45)

        # Footer with page number
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#003366"))
        self.drawRightString(self.width - 40, 20, f"Page {page} of {page_count}")

        # Add timestamp to footer
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.grey)
        footer_text = f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        self.drawString(40, 20, footer_text)

        self.restoreState()


def csv_to_pdf(csv_file, chainages, output_folder=None, report_info=None):
    # Default report information if not provided
    if report_info is None:
        report_info = {
            "Project": "Project Name",
            "Spread": "Spread Info",
            "File": os.path.basename(csv_file),
            "Base Point": "Base Point Info",
            "Point Number": "214 codes",
            "Control check": "0 Not entered",
            "Score": "100.00%"
        }

    # Ensure output directory exists
    if output_folder is None:
        output_folder = os.path.join(os.path.dirname(csv_file), '..', 'output', 'pdf')

    os.makedirs(output_folder, exist_ok=True)

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    output_pdf = os.path.join(output_folder, f"Survey_Report_{timestamp}.pdf")

    # Read and process CSV data
    df = pd.read_csv(csv_file, header=None, dtype=str, skiprows=1)
    if df.shape[1] < 5:
        raise ValueError(f"CSV file must have at least 5 columns, but found only {df.shape[1]} columns.")

    column_count = df.shape[1]
    base_columns = ["Point", "Northing", "Easting", "Elevation", "Description"]
    feature_columns = [f"Feature_{i}" for i in range(1, column_count - 4 + 1)]
    existing_feature_columns = feature_columns[:len(df.columns) - 5]
    df.columns = base_columns + existing_feature_columns

    df = df.astype(str).replace(["nan", "NaN", "NAN", "None"], "NA")

    # Process feature pairs
    feature_pairs = []
    for i in range(0, len(existing_feature_columns), 2):
        feature1 = existing_feature_columns[i]
        feature2 = existing_feature_columns[i + 1] if i + 1 < len(existing_feature_columns) else None

        feature_value1 = df[feature1].apply(extract_value)
        feature_value2 = df[feature2].apply(extract_value) if feature2 else pd.Series(["NA"] * len(df))

        feature_pairs.append(feature_value1)
        if feature2:
            feature_pairs.append(feature_value2)

    # Create FeatureName column
    df["FeatureName"] = [
        f"{desc}/{format_feature_name(row)}" if desc != "NA" else format_feature_name(row)
        for desc, row in zip(df["Description"], zip(*feature_pairs))
    ]

    # Calculate chainage and offset
    df["Chainage"] = None
    df["Offset"] = None
    polyline = data_to_polyline(chainages)
    df = calculate_chainage_offset(survey_df=df, polyline=polyline)

    # Select and organize columns
    df = df[["Point", "Northing", "Easting", "Elevation", "Description", "Chainage", "Offset", "FeatureName"]]
    df.fillna("N/A", inplace=True)

    # Set up the document
    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=landscape(A4),
        leftMargin=40,
        rightMargin=40,
        topMargin=120,  # Make room for header
        bottomMargin=40
    )

    # Create styles for text wrapping
    styles = getSampleStyleSheet()
    wrap_style = ParagraphStyle(
        name="WrapStyle",
        fontSize=9,
        leading=12,
        spaceBefore=1,
        spaceAfter=1
    )

    # Format descriptions for wrapping
    df["Description"] = df["Description"].apply(lambda x: Paragraph(str(x), wrap_style))
    df["FeatureName"] = df["FeatureName"].apply(lambda x: Paragraph(str(x), wrap_style))

    # Prepare table data
    data = [list(df.columns)] + df.values.tolist()

    # Adjust column widths for landscape
    col_widths = [0.8 * inch, 1.0 * inch, 1.0 * inch, 0.9 * inch, 1.1 * inch, 1.0 * inch, 1.0 * inch, 4.3 * inch]

    # Create table
    table = Table(data, colWidths=col_widths, repeatRows=1)

    # Define table styles
    num_align = [('ALIGN', (i, 1), (i, -1), 'RIGHT') for i in [0, 1, 2, 3, 5, 6]]
    desc_align = [('ALIGN', (4, 1), (4, -1), 'LEFT')]
    text_align = [('ALIGN', (7, 1), (7, -1), 'LEFT')]

    # Alternate row colors
    row_colors = []
    for i in range(1, len(data)):
        if i % 2 == 0:
            row_colors.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor("#f5f5f5")))

    # Apply all styles to table
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#003366")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('WORDWRAP', (4, 1), (7, -1)),
    ] + num_align + desc_align + text_align + row_colors))

    # Add elements to document
    elements = []
    elements.append(table)

    # Build the document with our custom canvas
    doc.build(elements, canvasmaker=lambda *args, **kwargs: MyCanvas(*args, report_info=report_info, **kwargs))

    print(f"✅ Official PDF report generated: {output_pdf}")
    return output_pdf