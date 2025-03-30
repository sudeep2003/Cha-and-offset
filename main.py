import pandas as pd
from csv_to_pdf import csv_to_pdf


def csv_to_list_of_dicts(csv_file):
    df = pd.read_csv(csv_file, header=None, dtype=str, skiprows=1)
    if df.shape[1] < 5:
        raise ValueError(f"CSV file must have at least 5 columns, but found only {df.shape[1]}.")

    base_columns = ["Point", "Easting", "Northing", "Chainage", "Description"]

    # Dynamically generate feature column names
    feature_columns = [f"Feature_{i}" for i in range(1, df.shape[1] - 4 + 1)]

    # Assign column names to DataFrame
    df.columns = base_columns + feature_columns[: len(df.columns) - 5]

    return df.to_dict(orient="records")  # Convert DataFrame to list of dicts


def main():
    csv_file = "./data/sample_data.csv"
    output_folder = "output"
    chainages_file = "./data/NPS 24 Proposed CL 2.csv"

    chainages_data = csv_to_list_of_dicts(chainages_file)

    pdf_path = csv_to_pdf(csv_file=csv_file, chainages=chainages_data, output_folder=output_folder, report_info=None)
    print(f"PDF generated at: {pdf_path}")


# Run the script
if __name__ == '__main__':
    main()
