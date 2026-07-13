# Input File Conversion Functions

# Imports
import io
import pandas as pd
import geopandas as gpd

# -- /upload endpoint --
def parse_file(filename: str, file_bytes: bytes) -> pd.DataFrame:
    """
    Parses the uploaded file and returns a GeoDataFrame
    """
    # File extension extraction
    ext = filename.lower().split(".")[-1]

    # CSV
    if ext == "csv":
        return _parse_csv(file_bytes)


def _parse_csv(file_bytes: bytes) -> pd.DataFrame:
    """
    Return dataframe based on input file
    """
    # Read CSV into a DataFrame
    df = pd.read_csv(io.BytesIO(file_bytes))
    return df

# -- /process endpoint --