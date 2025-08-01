from pinecone import Pinecone, ServerlessSpec
import numpy as np
import torch
from hana_utils import get_artist_metadata
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("trumuse-dev2")

# --- Vector Similarity Utilities ---

def get_clip_embedding(embedding_model, image):
    """
    Convert an image into a normalized CLIP embedding.
    """
    with torch.no_grad():
        image_features = embedding_model.encode_image(image)
    embedding = image_features[0].cpu().numpy()
    return embedding / np.linalg.norm(embedding)

def query_similar_vectors(query_vector, top_k=5):
    """
    Query Pinecone index to find top_k most similar vectors.
    Returns a list of (artist_id, similarity_score) tuples.
    """
    query_response = index.query(vector=query_vector.tolist(), top_k=top_k, include_metadata=True)

    results = []
    for match in query_response["matches"]:
        artist_id = int(match["id"])  # Convert ID to integer
        score = match["score"]
        results.append((artist_id, score))
    return results

def get_similar_artists_info(query_vector, top_k=3):
    """
    Combines similarity query and metadata fetch. 
    Returns artist info + similarity scores.
    """
    similar_vectors = query_similar_vectors(query_vector, top_k=top_k)
    artist_infos = []

    for artist_id, score in similar_vectors:
        metadata = get_artist_metadata(artist_id)
        if metadata:
            artist_infos.append({
                "artist_id": artist_id,
                "score": score,
                "metadata": metadata
            })
    return artist_infos

from PIL import Image
import clip

# Load CLIP
device = "cuda" if torch.cuda.is_available() else "cpu"
clip_model, preprocess = clip.load("ViT-B/32", device=device)

# So main.py can import the model directly
_all_ = ['get_clip_embedding', 'query_similar_vectors', 'clip_model', 'preprocess']