import os
import certifi
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError(
        "GROQ_API_KEY is missing. Please add it to your .env file."
    )

llm = ChatGroq(
    model="qwen/qwen3.8-27b",
    api_key=GROQ_API_KEY,
    temperature=0.3,
)