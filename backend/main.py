from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse, RedirectResponse, JSONResponse
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
import uuid
import json
import heatmap_generator
import logging
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    filename="backend.log",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filemode="a"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI()

# Mount the frontend folder as a static directory
app.mount("/frontend", StaticFiles(directory="../frontend"), name="frontend")

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def process_image_and_generate_report(image_path):
    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.debug(f"Using device: {device}")

        # Validate image file
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            raise HTTPException(status_code=400, detail="Image file not found on server")
        try:
            with PILImage.open(image_path) as img:
                input_image = preprocess(img).unsqueeze(0).to(device)
        except Exception as e:
            logger.error(f"Invalid image format for {image_path}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=400, detail=f"Invalid image format: {str(e)}")

        # Get CLIP embedding
        try:
            image_vector = get_clip_embedding(clip_model, input_image)
            logger.debug("Successfully generated CLIP embedding")
        except Exception as e:
            logger.error(f"CLIP embedding failure: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"CLIP embedding error: {str(e)}")

        # Query similar vectors from Pinecone
        try:
            similar_artists = query_similar_vectors(image_vector, top_k=5)
            logger.debug(f"Found {len(similar_artists)} similar artists")
        except Exception as e:
            logger.error(f"Pinecone query failed: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Pinecone query error: {str(e)}")

        # Fetch metadata and generate bio summaries
        artist_infos = []
        bio_summaries = {}
        for artist_id, score in similar_artists:
            try:
                logger.debug(f"Processing artist_id: {artist_id}")
                metadata = get_artist_metadata(artist_id)
                if not metadata:
                    logger.warning(f"No metadata for artist_id: {artist_id}")
                    continue
                wikipedia_url = metadata.get("wikipedia")
                bio = "(No Wikipedia summary available)"
                if wikipedia_url:
                    try:
                        bio = summarize_wikipedia_url(wikipedia_url)
                        logger.debug(f"Successfully summarized Wikipedia for {artist_id}")
                    except Exception as e:
                        logger.error(f"Wikipedia summary failed for {artist_id}: {str(e)}")
                bio_summaries[metadata.get("name", f"Artist_{artist_id}")] = bio
                artist_infos.append({"artist_id": artist_id, "score": score, "metadata": metadata})
            except Exception as e:
                logger.error(f"Failed to process artist {artist_id}: {str(e)}", exc_info=True)
                continue

        if not artist_infos:
            logger.error("No valid artist data retrieved")
            raise HTTPException(status_code=500, detail="No valid artist data retrieved")

        # Generate JSON for frontend
        html_friendly_data = []
        for info in artist_infos:
            metadata = info["metadata"]
            html_friendly_data.append({
                "id": str(metadata.get("id", "Unknown")),
                "name": str(metadata.get("name", "Unknown")),
                "years": str(metadata.get("years", "Unknown")),
                "genre": str(metadata.get("genre", "Unknown")),
                "nationality": str(metadata.get("nationality", "Unknown")),
                "similarity_score": float(round(info["score"] * 100, 2)),
                "bio": str(bio_summaries.get(metadata.get("name", f"Artist_{info['artist_id']}"), "(No bio)"))
            })

        # Save to JSON
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        JSON_PATH = os.path.join(BASE_DIR, "..", "frontend", "public", "matched_artists.json")
        try:
            os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
            with open(JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(html_friendly_data, f)
            logger.debug(f"Successfully wrote JSON to {JSON_PATH}")
        except Exception as e:
            logger.error(f"Failed to write JSON to {JSON_PATH}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to write JSON: {str(e)}")

        # Generate and save PDF
        pdf_buffer = io.BytesIO()
        try:
            generate_attribution_report(image_path, pdf_buffer, artist_infos, bio_summaries)
            logger.debug("Successfully generated PDF buffer")
        except Exception as e:
            logger.error(f"PDF generation failed: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"PDF generation error: {str(e)}")

        pdf_buffer.seek(0)
        PDF_PATH = os.path.join(BASE_DIR, "..", "frontend", "public", "attribution_report.pdf")
        try:
            os.makedirs(os.path.dirname(PDF_PATH), exist_ok=True)
            with open(PDF_PATH, "wb") as f:
                f.write(pdf_buffer.read())
            logger.debug(f"Successfully wrote PDF to {PDF_PATH}")
        except Exception as e:
            logger.error(f"Failed to write PDF to {PDF_PATH}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to write PDF: {str(e)}")

        pdf_buffer.seek(0)
        return pdf_buffer, html_friendly_data
    except Exception as e:
        logger.error(f"Unexpected error in process_image_and_generate_report: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@app.get("/", response_class=RedirectResponse)
async def redirect_to_artist_upload():
    return RedirectResponse(url="/frontend/public/artist-upload.html")

@app.post("/upload_and_download")
async def upload_and_download(image: UploadFile = File(...)):
    try:
        print(f"Received file: {image.filename}, content_type: {image.content_type}, size: {image.size}")
        logger.info(f"Received file: {image.filename}, content_type: {image.content_type}, size: {image.size}")

        # Validate file type and size
        if not image.content_type.startswith('image/'):
            logger.error(f"Invalid file type: {image.content_type}")
            raise HTTPException(status_code=400, detail="File must be an image")
        if image.size > 10 * 1024 * 1024:  # 10MB limit
            logger.error(f"File too large: {image.size} bytes")
            raise HTTPException(status_code=400, detail="File size exceeds 10MB")

        # Use unique temporary file name
        unique_id = str(uuid.uuid4())
        image_path = f"temp_{unique_id}_{image.filename}"
        try:
            with open(image_path, "wb") as buffer:
                buffer.write(await image.read())
            logger.debug(f"Successfully saved temporary image to {image_path}")
        except Exception as e:
            logger.error(f"Failed to save uploaded image {image_path}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to save image: {str(e)}")

        try:
            pdf_buffer, _ = process_image_and_generate_report(image_path)
        except HTTPException as e:
            if os.path.exists(image_path):
                os.remove(image_path)
            raise e
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}", exc_info=True)
            if os.path.exists(image_path):
                os.remove(image_path)
            raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

        if os.path.exists(image_path):
            try:
                os.remove(image_path)
                logger.debug(f"Successfully deleted temporary image {image_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temp image {image_path}: {str(e)}")

        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=Attribution_Report.pdf"}
        )
    except Exception as e:
        logger.error(f"Error in upload_and_download: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.get("/get_attribution_data")
async def get_attribution_data():
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        JSON_PATH = os.path.join(BASE_DIR, "..", "frontend", "public", "matched_artists.json")
        if not os.path.exists(JSON_PATH):
            logger.error(f"Attribution data not found at {JSON_PATH}")
            raise HTTPException(status_code=404, detail="Attribution data not found. Please upload an image first.")
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.debug("Successfully fetched attribution data")
        return JSONResponse(content=data)
    except Exception as e:
        logger.error(f"Error fetching attribution data: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")

@app.post("/compare_artworks")
async def compare_artworks(original_image: UploadFile = File(...), ai_image: UploadFile = File(...)):
    try:
        # Save both images temporarily
        original_path = f"temp_original_{original_image.filename}"
        ai_path = f"temp_ai_{ai_image.filename}"
        with open(original_path, "wb") as buffer:
            buffer.write(await original_image.read())
        with open(ai_path, "wb") as buffer:
            buffer.write(await ai_image.read())

        # Generate heatmap comparing the two images
        heatmap_buffer = io.BytesIO()
        heatmap_generator.generate_heatmap(original_path, ai_path, heatmap_buffer)
        heatmap_buffer.seek(0)

        # Clean up temporary files
        if os.path.exists(original_path):
            os.remove(original_path)
        if os.path.exists(ai_path):
            os.remove(ai_path)

        return StreamingResponse(
            heatmap_buffer,
            media_type="image/jpeg",
            headers={"Content-Disposition": "inline; filename=heatmap.jpg"}
        )
    except Exception as e:
        logger.error(f"Error comparing artworks: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)