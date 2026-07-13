# API Endpoints for Map Upload Container 

# Imports
import uuid
from datetime import datetime, timedelta
from fastapi import FastAPI, UploadFile, HTTPException, status
from converter import parse_file
from pydantic import BaseModel

# Variables from user input
class ProcessRequest(BaseModel):
    upload_id: str
    lat_col: str
    lon_col: str
    sum_cols: list[str]
    avg_cols: list[str]

# from h3_processor import aggregate_to_hex
# from map_builder import build_map

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

    # Throw excpetion for files larger than 10mb
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

@app.post("/process")
async def process_file(request: ProcessRequest):
    lat_col = request.lat_col
    lon_col = request.lon_col
    id = request.upload_id
    sum_cols = request.sum_cols
    avg_cols = request.avg_cols 