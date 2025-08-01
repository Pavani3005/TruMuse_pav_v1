from fastapi import FastAPI, Request, File, UploadFile
from fastapi.responses import StreamingResponse, HTMLResponse
from generate_report import generate_attribution_report
from hana_utils import get_artist_metadata
from vector_utils import get_clip_embedding, query_similar_vectors, clip_model, preprocess
from claude_utils import summarize_wikipedia_url
from PIL import Image as PILImage
import torch
from dotenv import load_dotenv
import io
import os
import logging
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Set up logging
logging.basicConfig(level=logging.DEBUG)  # Increased to DEBUG for more details
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")  # Serve static files
app.mount("/frontend", StaticFiles(directory="C:/Users/hp/Desktop/SAP_Hackathon/frontend"), name="frontend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
templates = Jinja2Templates(directory="template")  # Match your folder name

def process_image_and_generate_report(image_path):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    input_image = preprocess(PILImage.open(image_path)).unsqueeze(0).to(device)
    
    # Get CLIP embedding
    image_vector = get_clip_embedding(clip_model, input_image)
    
    # Query similar vectors from Pinecone
    similar_artists = query_similar_vectors(image_vector, top_k=5)
    
    # Fetch metadata and generate bio summaries
    artist_infos = []
    bio_summaries = {}
    for artist_id, score in similar_artists:
        metadata = get_artist_metadata(artist_id)
        if metadata and "wikipedia" in metadata and metadata["wikipedia"]:
            bio = summarize_wikipedia_url(metadata["wikipedia"])
        else:
            bio = "(No Wikipedia summary available)"
        bio_summaries[metadata.get("name", f"Artist_{artist_id}")] = bio
        artist_infos.append({
            "artist_id": artist_id,
            "score": score,
            "metadata": metadata
        })
    
    # Generate PDF in memory
    pdf_buffer = io.BytesIO()
    generate_attribution_report(image_path, pdf_buffer, artist_infos, bio_summaries)
    pdf_buffer.seek(0)
    return pdf_buffer

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    import os
    template_path = os.path.join(os.getcwd(), "template", "index.html")
    print(f"Looking for template at: {template_path}")
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload_and_download")
async def upload_and_download(image: UploadFile = File(...)):  # Changed from 'file' to 'image'
    try:
        # Debug: Print file details to terminal
        print(f"Received file: {image.filename}, content_type: {image.content_type}, size: {image.size}")
        logger.info(f"Received file: {image.filename}, content_type: {image.content_type}, size: {image.size}")
        
        # Save uploaded file temporarily
        image_path = f"temp_{image.filename}"
        with open(image_path, "wb") as buffer:
            buffer.write(await image.read())
        
        pdf_buffer = process_image_and_generate_report(image_path)
        
        # Clean up temporary file
        if os.path.exists(image_path):
            os.remove(image_path)
        
        # Use StreamingResponse for in-memory buffer
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=Attribution_Report.pdf"}
        )
    except Exception as e:
        logger.error(f"Error processing upload: {str(e)}", exc_info=True)  # Include full stack trace
        raise  # Re-raise to let FastAPI handle the error

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)