import nltk
import os
import sys

def setup_nltk_data():
    """Download and setup required NLTK data"""
    print("Setting up NLTK data...")
    
    # Create nltk_data directory in the project
    nltk_data_path = os.path.join(os.path.dirname(__file__), 'nltk_data')
    os.makedirs(nltk_data_path, exist_ok=True)
    
    # Add to NLTK path
    nltk.data.path.append(nltk_data_path)
    
    packages_to_download = [
        'punkt_tab',  # New tokenizer
        'stopwords',  # Stopwords corpus
        'punkt'       # Fallback tokenizer
    ]
    
    for package in packages_to_download:
        try:
            print(f"Downloading {package}...")
            nltk.download(package, download_dir=nltk_data_path, quiet=False)
            print(f"✓ {package} downloaded successfully")
        except Exception as e:
            print(f"✗ Failed to download {package}: {e}")
    
    print("\nNLTK setup completed!")

if __name__ == "__main__":
    setup_nltk_data()