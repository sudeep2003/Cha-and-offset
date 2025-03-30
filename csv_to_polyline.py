import pandas as pd
from shapely.geometry import LineString


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
