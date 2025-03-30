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
