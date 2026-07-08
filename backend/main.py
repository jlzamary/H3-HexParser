# API Endpoints for Map Upload Container 

# Imports
from fastapi import FastAPI, UploadFile
from converter import parse_file
from h3_processor import aggregate_to_hex
from map_builder import build_map

app = FastAPI()

# API endpoint to handle file uploads and generate H3 hex map
@app.post("/upload")
async def upload_file(file: UploadFile):
    # from converter.py
    df = parse_file(file)
    # from h3_processor.py              
    hex_df = aggregate_to_hex(df) 
    # from map_builder.py     
    map_html = build_map(hex_df)       
    return {"map_html": map_html}