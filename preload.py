import os
import sys

print("Downloading and caching HuggingFace Embeddings model...")
try:
    from langchain_huggingface import HuggingFaceEmbeddings
    # This will trigger the download and cache it in ~/.cache/huggingface
    model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    print("Successfully cached embeddings model!")
except Exception as e:
    print(f"Error caching model: {e}")
    sys.exit(1)
