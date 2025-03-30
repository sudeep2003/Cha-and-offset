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


def add_header_info(canvas, doc, report_info):
    """ Adds the header with Point Report title and additional info in a four-column layout. """
    canvas.saveState()

    # Page width for landscape A4
    page_width = landscape(A4)[0]

    # Title - Top left
    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawString(40, 550, "Point Report")

    # Calculate column positions (divide usable width into 4 equal columns)
    left_margin = 40
    col_width = (page_width - (left_margin * 2)) / 4

    col1 = left_margin
    col2 = left_margin + col_width
    col3 = left_margin + (col_width * 2)
    col4 = left_margin + (col_width * 3)

    # Set font for all info text
    canvas.setFont("Helvetica", 10)

    # First column
    y_pos = 530
    canvas.drawString(col1, y_pos, f"Project: {report_info.get('Project', '')}")
    canvas.drawString(col1, y_pos - 15, f"Spread: {report_info.get('Spread', '')}")
    canvas.drawString(col1, y_pos - 30, f"File: {report_info.get('File', '')}")

    # Second column
    canvas.drawString(col2, y_pos, f"Base Point: {report_info.get('Base Point', '')}")
    canvas.drawString(col2, y_pos - 15, f"Point Number: ")

    # Third column
    canvas.drawString(col3, y_pos, f"Control check: ")
    canvas.drawString(col3, y_pos - 15, f"Point Number: 5960890")

    # Fourth column
    canvas.drawString(col4, y_pos, f"{report_info.get('Point Number', '214 codes')}")
    canvas.drawString(col4, y_pos - 15, f"{report_info.get('Control check', '0 Not entered')}")
    canvas.drawString(col4, y_pos - 30, f"Score: {report_info.get('Score', '100.00%')}")

    canvas.restoreState()


def add_page_number(canvas, doc):
    """ Adds a page number at the bottom of each page. """
    page_num = canvas.getPageNumber()
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(780, 20, f"Page {page_num}")


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

    df = pd.read_csv(csv_file, header=None, dtype=str, skiprows=1)
    if df.shape[1] < 5:
        raise ValueError(f"CSV file must have at least 5 columns, but found only {df.shape[1]} columns.")

    column_count = df.shape[1]
    base_columns = ["Point", "Northing", "Easting", "Elevation", "Description"]
    feature_columns = [f"Feature_{i}" for i in range(1, column_count - 4 + 1)]
    existing_feature_columns = feature_columns[:len(df.columns) - 5]
    df.columns = base_columns + existing_feature_columns

    df = df.astype(str).replace(["nan", "NaN", "NAN", "None"], "NA")

    feature_pairs = []
    for i in range(0, len(existing_feature_columns), 2):
        feature1 = existing_feature_columns[i]
        feature2 = existing_feature_columns[i + 1] if i + 1 < len(existing_feature_columns) else None

        feature_value1 = df[feature1].apply(extract_value)
        feature_value2 = df[feature2].apply(extract_value) if feature2 else "NA"

        feature_pairs.append(feature_value1)
        if feature2:
            feature_pairs.append(feature_value2)

    df["FeatureName"] = [
        f"{desc}/{format_feature_name(row)}" if desc != "NA" else format_feature_name(row)
        for desc, row in zip(df["Description"], zip(*feature_pairs))
    ]

    df["Chainage"] = None
    df["Offset"] = None
    polyline = data_to_polyline(chainages)
    df = calculate_chainage_offset(survey_df=df, polyline=polyline)

    df = df[["Point", "Northing", "Easting", "Elevation", "Description", "Chainage", "Offset", "FeatureName"]]
    df.fillna("N/A", inplace=True)

    styles = getSampleStyleSheet()
    wrap_style = ParagraphStyle(name="WrapStyle", fontSize=9, leading=11)
    df["Description"] = df["Description"].apply(lambda x: Paragraph(str(x), wrap_style))
    df["FeatureName"] = df["FeatureName"].apply(lambda x: Paragraph(str(x), wrap_style))

    data = [list(df.columns)] + df.values.tolist()

    doc = SimpleDocTemplate(output_pdf, pagesize=landscape(A4), leftMargin=40, rightMargin=40, topMargin=120,
                            bottomMargin=40)

    elements = []
    # Remove the title from elements as we'll add it directly to the canvas
    elements.append(Spacer(1, 12))

    col_widths = [1.0 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch, 1.2 * inch, 4.0 * inch]
    table = Table(data, colWidths=col_widths)

    num_align = [('ALIGN', (i, 1), (i, -1), 'RIGHT') for i in [0, 1, 2, 3, 5, 6]]
    desc_align = [('ALIGN', (4, 1), (4, -1), 'LEFT')]
    text_align = [('ALIGN', (7, 1), (7, -1), 'LEFT')]

    table.setStyle(TableStyle([
                                  ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#003366")),
                                  ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                                  ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                                  ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                  ('FONTSIZE', (0, 0), (-1, 0), 9),
                                  ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                                  ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                                  ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                                  ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                  ('LEFTPADDING', (0, 0), (-1, -1), 6),
                                  ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                                  ('WORDWRAP', (6, 1), (7, -1)),
                              ] + num_align + desc_align + text_align))

    elements.append(table)

    def on_draw(canvas, doc):
        """ Function to draw header and page numbers on each page. """
        add_header_info(canvas, doc, report_info)
        add_page_number(canvas, doc)

    # Add Page Template for header and page numbering
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height - 80, id="normal")
    doc.addPageTemplates([PageTemplate(id="PageNumber", frames=frame, onPage=on_draw)])

    doc.build(elements, onFirstPage=on_draw, onLaterPages=on_draw)

    print(f"✅ Official PDF report generated: {output_pdf}")
    return output_pdf  # Return the full path of the generated PDF