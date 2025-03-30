import os
import time
import pandas as pd
from weasyprint import HTML
import numpy as np
from shapely.geometry import LineString, Point
from scipy.spatial import KDTree


def calculate_chainage_offset(survey_df, polyline):
    """ Match survey points to polyline and calculate Chainage & Offset """

    # Ensure required columns exist
    required_columns = {"Point", "Northing", "Easting"}
    if not required_columns.issubset(survey_df.columns):
        raise ValueError(f"Survey CSV must contain {required_columns} columns")

    if (isinstance(survey_df["Easting"].iloc[0], str) and
            survey_df["Easting"].iloc[0] == "Easting"):
        # Skip the header row
        survey_df = survey_df.iloc[1:].reset_index(drop=True)

    # Convert polyline into coordinate list and create KDTree for fast searching
    polyline_points = np.array(polyline.coords)
    polyline_tree = KDTree(polyline_points)

    chainage_list = []
    offset_list = []

    for _, row in survey_df.iterrows():
        survey_point = Point(row["Easting"], row["Northing"])

        # Find nearest point on polyline
        _, nearest_index = polyline_tree.query([survey_point.x, survey_point.y])
        nearest_point = Point(polyline_points[nearest_index])

        # Compute accurate chainage using project() function
        chainage = round(polyline.project(nearest_point), 3)

        # Compute perpendicular offset distance
        offset = round(survey_point.distance(nearest_point), 3)

        chainage_list.append(chainage)
        offset_list.append(offset)

    # Add calculated values to DataFrame
    survey_df["Chainage"] = chainage_list
    survey_df["Offset"] = offset_list

    return survey_df


def data_to_polyline(data):
    """ Convert a list of objects (database records) into a polyline """

    # Convert data to a DataFrame (if it's not already)
    df = pd.DataFrame(data)

    # Check required columns
    required_columns = {"Point", "Northing", "Easting", "Chainage"}
    if not required_columns.issubset(df.columns):
        raise ValueError(f"Data must contain {required_columns} columns")

    # Remove rows with missing values
    df = df.dropna(subset=["Northing", "Easting", "Chainage"])

    # Ensure chainages are sorted correctly
    df = df.sort_values(by="Chainage", ascending=True)

    # Create a list of (Easting, Northing) points
    coordinates = list(zip(df["Easting"], df["Northing"]))

    # Convert into a polyline (LineString)
    polyline = LineString(coordinates)

    return polyline


def format_feature_name(features):
    """ Converts feature pairs into a formatted string. """
    feature_list = []

    for i in range(0, len(features), 2):
        feature_key = features[i]
        feature_value = features[i + 1] if i + 1 < len(features) else "NA"

        if feature_key == "NA" and feature_value == "NA":
            continue

        formatted_feature = f"{feature_key}={feature_value}"
        feature_list.append(formatted_feature)

    feature_name = "/".join(feature_list).strip("/")
    return feature_name if feature_name else "NA"


def extract_value(feature_value):
    """ Extracts the part after ':' if it exists. """
    if pd.isna(feature_value) or feature_value in ["nan", "NaN", "NAN"]:
        return "NA"
    return feature_value.split(":")[-1].strip() if ":" in feature_value else feature_value


def csv_to_pdf(csv_file, chainages, output_folder=None, report_info=None):
    """ Convert a CSV file to a styled PDF report using WeasyPrint. """

    # Default metadata
    if report_info is None:
        report_info = {
            "Project": "Project Name",
            "Spread": "Spread Info",
            "File": os.path.basename(csv_file),
            "Base Point": "Base Point Info",
            "Point Number": "214 codes",
            "Control check": "0 Not entered",
            "Score": "100.00%",
        }

    # Ensure output directory exists
    if output_folder is None:
        output_folder = os.path.join(os.path.dirname(csv_file), "..", "output", "pdf")
    os.makedirs(output_folder, exist_ok=True)

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    output_pdf = os.path.join(output_folder, f"Survey_Report_{timestamp}.pdf")

    # Load CSV data
    df = pd.read_csv(csv_file, header=None, dtype=str, skiprows=1)
    if df.shape[1] < 5:
        raise ValueError(f"CSV file must have at least 5 columns, but found only {df.shape[1]}.")

    # Define columns
    base_columns = ["Point", "Northing", "Easting", "Elevation", "Description"]
    feature_columns = [f"Feature_{i}" for i in range(1, df.shape[1] - 4 + 1)]
    df.columns = base_columns + feature_columns[: len(df.columns) - 5]

    df = df.astype(str).replace(["nan", "NaN", "NAN", "None"], "NA")

    # Format feature pairs
    feature_pairs = []
    for i in range(0, len(feature_columns), 2):
        feature1 = feature_columns[i]
        feature2 = feature_columns[i + 1] if i + 1 < len(feature_columns) else None

        feature_value1 = df[feature1].apply(extract_value)
        feature_value2 = df[feature2].apply(extract_value) if feature2 else "NA"

        feature_pairs.append(feature_value1)
        if feature2:
            feature_pairs.append(feature_value2)

    df["FeatureName"] = [
        f"{desc}/{format_feature_name(row)}" if desc != "NA" else format_feature_name(row)
        for desc, row in zip(df["Description"], zip(*feature_pairs))
    ]

    # Calculate Chainage and Offset
    df["Chainage"] = None
    df["Offset"] = None
    polyline = data_to_polyline(chainages)
    df = calculate_chainage_offset(survey_df=df, polyline=polyline)

    df = df[["Point", "Northing", "Easting", "Elevation", "Description", "Chainage", "Offset", "FeatureName"]]
    df.fillna("N/A", inplace=True)

    # Convert DataFrame to HTML
    table_html = df.to_html(index=False, escape=False)

    # Define the HTML template for WeasyPrint
    html_template = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 40px;
            }}
            .header {{
                text-align: left;
                font-size: 14px;
                margin-bottom: 20px;
            }}
            .header h1 {{
                color: #003366;
                font-size: 20px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 12px;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }}
            th {{
                background-color: #003366;
                color: white;
            }}
            .footer {{
                text-align: right;
                font-size: 12px;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>

        <div class="header">
            <h1>Point Report</h1>
            <p><strong>Project:</strong> {report_info['Project']} &nbsp;&nbsp;
               <strong>Spread:</strong> {report_info['Spread']} &nbsp;&nbsp;
               <strong>File:</strong> {report_info['File']}</p>
            <p><strong>Base Point:</strong> {report_info['Base Point']} &nbsp;&nbsp;
               <strong>Point Number:</strong> {report_info['Point Number']} &nbsp;&nbsp;
               <strong>Control Check:</strong> {report_info['Control check']} &nbsp;&nbsp;
               <strong>Score:</strong> {report_info['Score']}</p>
        </div>

        {table_html}

        <div class="footer">
            Page <span class="pageNumber"></span>
        </div>

    </body>
    </html>
    """

    # Convert HTML to PDF
    HTML(string=html_template).write_pdf(output_pdf)

    print(f"✅ PDF report generated: {output_pdf}")
    return output_pdf  # Return generated PDF path


def csv_to_list_of_dicts(csv_file):
    df = pd.read_csv(csv_file, header=None, dtype=str)
    if df.shape[1] < 5:
        raise ValueError(f"CSV file must have at least 5 columns, but found only {df.shape[1]}.")

    base_columns = ["Point", "Easting", "Northing", "Elevation", "Description"]

    # Dynamically generate feature column names
    feature_columns = [f"Feature_{i}" for i in range(1, df.shape[1] - 4 + 1)]

    # Assign column names to DataFrame
    df.columns = base_columns + feature_columns[: len(df.columns) - 5]

    return df.to_dict(orient="records")  # Convert DataFrame to list of dicts


def main():
    csv_file = "sample_data.csv"
    output_folder = "output"
    chainages_file = "NPS 24 Proposed CL 2.csv"

    chainages_data = csv_to_list_of_dicts(chainages_file)

    pdf_path = csv_to_pdf(csv_file=csv_file, chainages=chainages_data, output_folder=output_folder, report_info=None)
    print(f"PDF generated at: {pdf_path}")


# Run the script
if __name__ == '__main__':
    main()

