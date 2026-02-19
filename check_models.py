
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=api_key)

with open('models_utf8.txt', 'w', encoding='utf-8') as f:
    f.write(f"GenAI Version: {genai.__version__}\n")
    f.write("\n--- Available Models ---\n")
    for m in genai.list_models():
        if 'embed' in m.name:
            f.write(f"Name: {m.name}\n")
            f.write(f"Methods: {m.supported_generation_methods}\n")
            
print("Done writing to models_utf8.txt")
