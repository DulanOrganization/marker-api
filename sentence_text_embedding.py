from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModel
import torch
import logging
import uvicorn
from typing import List


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

class TextsInput(BaseModel):
    texts: List[str]

device = "cuda" if torch.cuda.is_available() else "cpu"

model_name = "sentence-transformers/all-MiniLM-L6-v2"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name).to(device)

def mean_pooling(model_output, attention_mask):
    # Mean Pooling - Take the mean of all token embeddings for the tokens in the sentence
    token_embeddings = model_output[0]  # First element is the last hidden states
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, dim=1) / torch.clamp(input_mask_expanded.sum(dim=1), min=1e-9)

@app.post("/get_embeddings")
async def get_embeddings(input_data: TextsInput):
    # Tokenize the input text
    encoded_input = tokenizer(input_data.texts, padding=True, truncation=True, return_tensors='pt').to(device)

    # Get the last hidden states
    with torch.no_grad():
        model_output = model(**encoded_input)

    # Apply mean pooling to get sentence embeddings
    embeddings = mean_pooling(model_output, encoded_input['attention_mask'])
    embeddings_list = embeddings.cpu().tolist()

    return {"embeddings": embeddings_list}


if __name__ == "__main__":
    uvicorn.run("sentence_text_embedding:app", host="0.0.0.0", port=8020, workers=3, reload=False)