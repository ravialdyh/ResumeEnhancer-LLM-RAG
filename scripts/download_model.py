from sentence_transformers import SentenceTransformer
import os

def download():
    """
    Downloads the sentence-transformer model from Hugging Face and saves it locally.
    This script is intended to be run during the Docker image build process.
    """
    model_name = 'all-MiniLM-L6-v2'
    save_path = '/app/models/all-MiniLM-L6-v2'
    
    if not os.path.exists(save_path):
        print(f"Downloading model '{model_name}' to '{save_path}'...")
        model = SentenceTransformer(model_name)
        model.save(save_path)
        print("Model downloaded and saved successfully.")
    else:
        print(f"Model already exists at '{save_path}'. Skipping download.")

if __name__ == "__main__":
    download()