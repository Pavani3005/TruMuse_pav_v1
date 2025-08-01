import torch
import clip
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
import numpy as np
import matplotlib.pyplot as plt
from torchvision import transforms

# --- Load CLIP model ---
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

# --- Config ---
PATCH_SIZE = 32

# --- Load and process image ---
def load_image(path, max_size=512):
    img = Image.open(path).convert("RGB")
    if img.size[0] > max_size or img.size[1] > max_size:
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    return img

def split_into_patches(image, patch_size):
    transform = transforms.ToTensor()
    img_tensor = transform(image)
    c, h, w = img_tensor.shape
    patches = img_tensor.unfold(1, patch_size, patch_size).unfold(2, patch_size, patch_size)
    patches = patches.contiguous().view(c, -1, patch_size, patch_size).permute(1, 0, 2, 3)
    return patches, h, w

def get_patch_embeddings(patches):
    embeddings = []
    for patch in patches:
        img = transforms.ToPILImage()(patch)
        inp = preprocess(img).unsqueeze(0).to(device)
        with torch.no_grad():
            emb = model.encode_image(inp).squeeze(0)
        embeddings.append(emb)
    return torch.stack(embeddings)

def compute_similarity(patch_embs, artist_emb):
    patch_embs = patch_embs / patch_embs.norm(dim=1, keepdim=True)
    artist_emb = artist_emb / artist_emb.norm()
    sim_scores = torch.nn.functional.cosine_similarity(patch_embs, artist_emb.unsqueeze(0), dim=1)
    return sim_scores

def create_heatmap(sim_scores, h, w, patch_size):
    grid_h = h // patch_size
    grid_w = w // patch_size
    heatmap = sim_scores.view(grid_h, grid_w).cpu().numpy()
    return heatmap

def overlay_heatmap(original_img, heatmap, output_path="output_heatmap.jpg"):
    import cv2

    # Resize heatmap to match image size
    heatmap_resized = cv2.resize(heatmap, original_img.size, interpolation=cv2.INTER_CUBIC)
    
    # Normalize to 0-255 and convert to uint8
    heatmap_norm = np.uint8(255 * (heatmap_resized - np.min(heatmap_resized)) / (np.max(heatmap_resized) - np.min(heatmap_resized)))

    # Apply colormap
    heatmap_color = cv2.applyColorMap(heatmap_norm, cv2.COLORMAP_JET)

    # Convert PIL image to OpenCV format
    img_np = np.array(original_img)
    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

    # Blend images
    blended = cv2.addWeighted(img_bgr, 0.6, heatmap_color, 0.4, 0)

    # Show and save result
    cv2.imshow("Overlay Heatmap", blended)
    cv2.imwrite(output_path, blended)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

# --- Main execution ---
uploaded_img = load_image("uploaded.jpg")
artist_img = load_image("artist.jpg")

uploaded_patches, h, w = split_into_patches(uploaded_img, PATCH_SIZE)
patch_embeddings = get_patch_embeddings(uploaded_patches)

# Get full image embedding for artist
artist_tensor = preprocess(artist_img).unsqueeze(0).to(device)
with torch.no_grad():
    artist_embedding = model.encode_image(artist_tensor).squeeze(0)

# Compute similarity + heatmap
similarities = compute_similarity(patch_embeddings, artist_embedding)
heatmap = create_heatmap(similarities, h, w, PATCH_SIZE)

# Display heatmap
overlay_heatmap(uploaded_img, heatmap)
