from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from typing import List
from PIL import Image
from pydantic import BaseModel
from transformers import CLIPModel, CLIPProcessor
import torch
import io
import base64
import logging
import uvicorn

logger = logging.getLogger(__name__)

app = FastAPI()

logger.info("Configuring CORS middleware")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

class EmbeddingsRequest(BaseModel):
    texts: List[str]
    images: List[str]
    
class CLIPService:
    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)

    def text2vec(self, texts: List[str]) -> torch.Tensor:
        inputs = self.processor(text=texts, return_tensors="pt", padding=True, truncation=True).to(self.device)
        with torch.no_grad():
            text_embeds = self.model.get_text_features(**inputs)
        return text_embeds

    def images2vec(self, images: List[Image.Image], normalize: bool = True) -> torch.Tensor:
        inputs = self.processor(images=images, return_tensors="pt")
        with torch.no_grad():
            model_inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
            # Extract visual embeddings from the vision model
            image_embeds = self.model.vision_model(**model_inputs)
            # image_embeds is a tuple: (last_hidden_state, pooler_output)
            # pooler_output is at index 1
            clip_vectors = self.model.visual_projection(image_embeds[1])
        if normalize:
            clip_vectors = clip_vectors / clip_vectors.norm(dim=-1, keepdim=True)
        return clip_vectors


app = FastAPI()

clip_service = CLIPService()

@app.post("/get_embeddings")
async def get_embeddings(req: EmbeddingsRequest):
    # Process text embeddings
    text_embeds = clip_service.text2vec(req.texts)
    text_embeddings_list = text_embeds.cpu().tolist()

    # Decode base64 images into PIL Images
    pil_images = []
    for img_b64 in req.images:
        image_bytes = base64.b64decode(img_b64)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        pil_images.append(image)

    # Process image embeddings
    if len(pil_images) > 0:
        image_embeds = clip_service.images2vec(pil_images)
        image_embeddings_list = image_embeds.cpu().tolist()
    else:
        image_embeddings_list = []

    return {
        "text_embeddings": text_embeddings_list,
        "image_embeddings": image_embeddings_list
    }
    
if __name__ == "__main__":
    uvicorn.run("image_embedding:app", host="0.0.0.0", port=8030, workers=3, reload=False)