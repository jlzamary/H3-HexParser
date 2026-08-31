# Input File Conversion Functions
from __future__ import annotations

# Imports
import io
import json
from html import escape as _esc
import h3
import folium
import pandas as pd
import geopandas as gpd
import branca

# tab20 color palette
TAB20_COLORS = [
    "#1f77b4", "#ff7f0e", "#ffbb78", "#2ca02c", "#98df8a",
    "#d62728", "#ff9896", "#9467bd", "#c5b0d5", "#8c564b",
    "#e377c2", "#7f7f7f", "#c7c7c7", "#bcbd22", "#dbdb8d",
    "#17becf", "#9edae5",
]

## /upload endpoint
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

## /process endpoint
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
    can still be centered afterwards. Aggregated columns are suffixed with
    "_sum"/"_mean" so the same input column can be both summed and
    averaged without one overwriting the other.
    """
    # Named aggregation 
    named_aggs = {
        boundary_col: (boundary_col, "first"),
        lat_col: (lat_col, "mean"),
        lon_col: (lon_col, "mean"),
    }
    named_aggs.update({f"{col}_sum": (col, "sum") for col in sum_cols})
    named_aggs.update({f"{col}_mean": (col, "mean") for col in avg_cols})

    # Group by H3 index and aggregate
    grouped = df.groupby(h3_col, as_index=False).agg(**named_aggs)

    # Row count per hexagon, merged in separately since it isn't a
    # per-column aggregation
    counts = df.groupby(h3_col, as_index=False).size().rename(columns={"size": "count"})
    return grouped.merge(counts, on=h3_col)


def hex_value_fields(sum_cols: list[str], avg_cols: list[str]) -> list[str]:
    """
    Names of the aggregated columns available to color the hex map by,
    in the order they should be offered to the user. "count" is always
    first since it's always available.
    """
    fields = ["count"]
    fields.extend(f"{col}_sum" for col in sum_cols)
    fields.extend(f"{col}_mean" for col in avg_cols)
    return fields

def build_field_colormaps(df: pd.DataFrame, fields: list[str]) -> dict[str, branca.colormap.LinearColormap]:
    """
    Build one white -> base-color linear colormap per field, scaled to
    that field's own min/max. Each field gets a distinct base color from
    the tab20 palette so the fields stay visually distinguishable when
    toggled between.
    """
    colormaps = {}
    for i, field in enumerate(fields):
        base_color = TAB20_COLORS[i % len(TAB20_COLORS)]
        vmin, vmax = df[field].min(), df[field].max()
        if vmin == vmax:
            # LinearColormap needs a non-zero range to scale against
            vmax = vmin + 1
        colormaps[field] = branca.colormap.LinearColormap(colors=["#ffffff", base_color], vmin=vmin, vmax=vmax)
    return colormaps


def map_h3(df: pd.DataFrame, boundary_col: str, lat_col: str, lon_col: str,
           color_fields: list[str] | None = None, zoom_start: int = 8) -> folium.Map:
    """
    Create a Folium map with H3 hexagons. When more than one color_field
    is given, each becomes a mutually-exclusive radio layer (via
    LayerControl) so the user can pick which aggregated field drives the
    color ramp; a matching legend is swapped in alongside it.
    """
    if not color_fields:
        color_fields = ["count"]

    # Compute central location
    center_lat, center_lon = _center_coords(df, lat_col=lat_col, lon_col=lon_col)

    # Initialize the map
    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom_start, tiles=None)
    folium.TileLayer("cartodbdark_matter", control=False).add_to(m)

    colormaps = build_field_colormaps(df, color_fields)

    legend_entries = []  # (dom_id, label, base_color, vmin, vmax)
    for i, field in enumerate(color_fields):
        colormap = colormaps[field]
        base_color = TAB20_COLORS[i % len(TAB20_COLORS)]
        label = _esc(field)
        dom_id = f"hex-legend-{i}"
        legend_entries.append((dom_id, label, base_color, colormap.vmin, colormap.vmax))

        # Radio-selectable (overlay=False) layer group, one per field, so
        # only one field's coloring is shown at a time
        layer = folium.FeatureGroup(name=label, overlay=False, show=(i == 0))

        for _, row in df.iterrows():
            value = row[field]
            color = colormap(value)
            boundary = row[boundary_col]
            folium.Polygon(locations=boundary,
                           color=color,
                           fill=True,
                           weight=2,
                           fill_color=color,
                           fill_opacity=0.65,
                           tooltip=f"{label}: {value:.2f}"
                           ).add_to(layer)

        layer.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    # Small always-in-DOM legend per field; a script toggles which one is
    # visible to match the layer picked in LayerControl above
    legend_html = ['<div style="position: fixed; bottom: 30px; left: 10px; z-index: 9999; '
                   'background: white; padding: 8px 10px; border-radius: 4px; '
                   'box-shadow: 0 1px 4px rgba(0,0,0,0.4); font: 12px/1.4 sans-serif;">']
    for dom_id, label, base_color, vmin, vmax in legend_entries:
        display = "block" if dom_id == legend_entries[0][0] else "none"
        legend_html.append(
            f'<div id="{dom_id}" style="display:{display};">'
            f'<div style="font-weight:600;">{label}</div>'
            f'<div style="width:150px; height:10px; '
            f'background: linear-gradient(to right, #ffffff, {base_color}); border:1px solid #999;"></div>'
            f'<div style="display:flex; justify-content:space-between;">'
            f'<span>{vmin:.2f}</span><span>{vmax:.2f}</span></div>'
            f'</div>'
        )
    legend_html.append('</div>')
    m.get_root().html.add_child(folium.Element("".join(legend_html)))

    # Map field label and legend dom id
    legend_lookup = json.dumps({label: dom_id for dom_id, label, *_ in legend_entries}).replace("<", "\\u003c")
    toggle_script = f"""
    (function() {{
        var legendIds = {legend_lookup};
        function showLegend(field) {{
            Object.keys(legendIds).forEach(function(key) {{
                var el = document.getElementById(legendIds[key]);
                if (el) {{ el.style.display = (key === field) ? "block" : "none"; }}
            }});
        }}
        window.addEventListener("load", function() {{
            {m.get_name()}.on("baselayerchange", function(e) {{ showLegend(e.name); }});
        }});
    }})();
    """
    m.get_root().script.add_child(folium.Element(toggle_script))

    # Return final map object
    return m