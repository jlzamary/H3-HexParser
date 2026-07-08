# Input File Conversion Functions

# Imports
import geopandas as gpd

def parse_file(filename: str, file_bytes: bytes) -> gpd.GeoDataFrame:
    """
    Parses the uploaded file and returns a GeoDataFrame
    """
    # File extension extraction
    ext = filename.lower().split(".")[-1]

    # CSV
    if ext == "csv":
        return _parse_csv(file_bytes)


def _parse_csv(file_bytes: bytes) -> gpd.GeoDataFrame:
    """"  
    """