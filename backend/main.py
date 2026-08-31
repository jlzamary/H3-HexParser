# API Endpoints for Map Upload Container 

# Imports
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import FastAPI, UploadFile, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from converter import parse_file, compute_h3_and_boundaries, aggregate_to_hex, hex_value_fields, map_h3
from pydantic import BaseModel

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# Variables from user input
class ProcessRequest(BaseModel):
    upload_id: str
    lat_col: str
    lon_col: str
    sum_cols: list[str]
    avg_cols: list[str]
    resolution: int

app = FastAPI()
_upload_cache: dict[str, dict] = {}

# API endpoint to handle file uploads and generate H3 hex map
@app.post("/upload")
async def upload_file(file: UploadFile):
    # Read the raw bytes from the upload
    # since UploadFile.read() is async (it streams from disk/network)
    file_bytes = await file.read()

    # Check file size
    file_size = len(file_bytes)

    # Throw exception for files larger than 10mb
    MAX_FILE_SIZE = 10 * 1024 * 1024 

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds the 10MB limit.")
    
    # Generate Unique Query ID
    upload_id = str(uuid.uuid4())

    # Get file name
    filename = file.filename

    # Now matches parse_file(filename: str, file_bytes: bytes)
    df = parse_file(filename, file_bytes)

    # Set upload cache with the dataframe and timestamp
    _upload_cache[upload_id] = {"df": df, "created_at": datetime.now()}

    # Return to frontend 
    return {"upload_id": upload_id, "columns": list(df.columns)}

@app.post("/process", response_class=HTMLResponse)
async def process_file(request: ProcessRequest):
    lat_col = request.lat_col
    lon_col = request.lon_col
    id = request.upload_id
    sum_cols = request.sum_cols
    avg_cols = request.avg_cols 
    resolution = request.resolution

    # Raise error if upload_id not found in cache
    if id not in _upload_cache:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload ID not found. Please upload a file first."
        )
    
    # Assign the dataframe from the cache
    df = _upload_cache[id]["df"]
    
    # Compute H3 index and boundaries for the dataframe
    df[["h3_index", "boundary"]] = df.apply(compute_h3_and_boundaries, lon_col=lon_col, lat_col=lat_col, resolution=resolution, axis=1)

    # Aggregate rows down to one per hexagon, summing/averaging the requested columns
    df = aggregate_to_hex(df, h3_col="h3_index", boundary_col="boundary",
                          lat_col=lat_col, lon_col=lon_col, sum_cols=sum_cols, avg_cols=avg_cols,)

    # Build the HTML map, offering a toggle between count and each
    # sum/avg column the user asked to aggregate
    color_fields = hex_value_fields(sum_cols, avg_cols)
    output_map = map_h3(df, boundary_col="boundary", lat_col=lat_col, lon_col=lon_col, color_fields=color_fields)

    # Return the map's own standalone HTML document
    return output_map.get_root().render()

# Serve the frontend (must be mounted last so it doesn't shadow the API routes above)
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")