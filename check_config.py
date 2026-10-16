
import os
from dotenv import load_dotenv

# Load values from the local .env file
load_dotenv()

# Read the API key without printing it
api_key = os.getenv("NUGEN_API_KEY")

if api_key:
    print("SUCCESS: Nugen API key loaded.")
else:
    print("ERROR: API key not found. Check your .env file.")
