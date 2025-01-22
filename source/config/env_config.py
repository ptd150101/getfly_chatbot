from dotenv import load_dotenv
import os
load_dotenv("./credentials/.env")  # take environment variables from .env.

LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST")

DB_HOST=os.getenv("DB_HOST")
DB_NAME=os.getenv("DB_NAME")
DB_PASSWORD=os.getenv("DB_PASSWORD")
DB_PORT=os.getenv("DB_PORT")
DB_USER=os.getenv("DB_USER")
DB_URL=f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"






DEFAULT_ANSWER = os.getenv("DEFAULT_ANSWER")
CREDENTIALS_PATH = os.getenv("CREDENTIALS_PATH")

OVERLOAD_MESSAGE=os.getenv("OVERLOAD_MESSAGE")
CS_MESSAGE=os.getenv("CS_MESSAGE")
NO_RELEVANT_GETFLY_MESSAGE=os.getenv("NO_RELEVANT_GETFLY_MESSAGE")
