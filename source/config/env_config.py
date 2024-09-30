from dotenv import load_dotenv
import os
load_dotenv("./credentials/.env")  # take environment variables from .env.

RUNTIME_ENVIRONMENT = os.getenv("RUNTIME_ENVIRONMENT")
PORT_NUMBER = int(os.getenv("PORT_NUMBER", 6379))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MILVUS_USERNAME = os.getenv("MILVUS_USERNAME")
MILVUS_PASSWORD = os.getenv("MILVUS_PASSWORD")
MILVUS_HOST = os.getenv("MILVUS_HOST")
MILVUS_PORT = os.getenv("MILVUS_PORT")
MILVUS_DB = os.getenv("MILVUS_DB")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST")
TF_ENABLE_ONEDNN_OPTS = os.environ['TF_ENABLE_ONEDNN_OPTS']
TF_CPP_MIN_LOG_LEVEL = os.environ['TF_CPP_MIN_LOG_LEVEL']
GOOGLE_CLOUD_PROJECT = os.environ['GOOGLE_CLOUD_PROJECT']