# Input File Conversion Functions

# Imports
import io
import h3
import folium
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

def compute_h3_and_boundaries(row, resolution: int, lat_col: str, lon_col: str) -> pd.Series:
    """
    Add H3 index and boundary columns
    """
    # Calculate H3 based on lat/lon columns
    lat = row[lat_col]
    lng = row[lon_col]
    h3_index = h3.latlng_to_cell(lat, lng, res=resolution)
    boundary = h3.cell_to_boundary(h3_index)
    # Return results as a named series so they can be assigned as columns
    return pd.Series([h3_index, boundary], index=["h3_index", "boundary"])

def _center_coords(df: pd.DataFrame, lat_col: float, lon_col: float) -> tuple:
    """
    Get the center of all coordinates in a DataFrame
    """
    # Calculate the mean latitude and longitude
    mean_lat = df[lat_col].mean()
    mean_lon = df[lon_col].mean()
    
    return (mean_lat, mean_lon)

def aggregate_to_hex(df: pd.DataFrame, h3_col: str, boundary_col: str, lat_col: str, lon_col: str,
                      sum_cols: list[str], avg_cols: list[str]) -> pd.DataFrame:
    """
    Aggregate rows down to one row per H3 hexagon, summing sum_cols and
    averaging avg_cols. lat_col/lon_col are kept (averaged) so the map
    can still be centered afterwards.
    """
    agg_dict = {boundary_col: "first", lat_col: "mean", lon_col: "mean"}
    agg_dict.update({col: "sum" for col in sum_cols})
    agg_dict.update({col: "mean" for col in avg_cols})

    return df.groupby(h3_col, as_index=False).agg(agg_dict)

def map_h3(df: pd.DataFrame, boundary_col: str, lat_col: str, lon_col: str, zoom_start: int = 5) -> folium.Map:
    """
    Create a Folium map with H3 hexagons
    """
    # Compute central location
    center_lat, center_lon = _center_coords(df, lat_col = lat_col, lon_col = lon_col)

    # Initialize the map
    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom_start, tiles='cartodbpositron')

    # Add H3 hexagons to the map
    for _, row in df.iterrows():
        boundary = row[boundary_col]
        folium.Polygon(locations=boundary, 
                       color='grey', 
                       fill=True, 
                       fill_opacity=0.25
                       ).add_to(m)

    # Return final map object
    return m