# from langfuse.decorators import observe
# from utils.log_utils import get_logger
# from openai import OpenAI
# from typing import List, Optional
# import os

# logger = get_logger(__name__)


# class Embedder:
#     def __init__(
#         self,
#         model: str = "text-embedding-3-small",
#         api_key: str = os.getenv("OPENAI_API_KEY"),
#         base_url: Optional[str] = None,
#     ) -> None:
#         self.model = model
#         self.client = OpenAI(api_key=api_key, base_url=base_url)

#     @observe(name="Embedder")
#     def run(self, text: str) -> List[float]:
#         response = self.client.embeddings.create(model=self.model, input=text)
#         return response.data[0].embedding



"""Embedder sử dụng API của Communi"""
from langfuse.decorators import observe
import requests
import json
from typing import List
import time


class Embedder:
    def __init__(
        self,
        url: str = "http://35.197.153.145:8231/embed",
        batch_size: int = 1,
        max_length: int = 4096,
        max_retries: int = 20,
        retry_delay: float = 2.0
    ) -> None:
        self.url = url
        self.batch_size = batch_size
        self.max_length = max_length
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    @observe(name="Embedder")
    def run(self, text: str) -> List[float]:
        payload = json.dumps({
            "sentences": [text],
            "params": {
                "batch_size": self.batch_size,
                "max_length": self.max_length
            },
            "embedding_types": {
                "dense": True,
                "sparse": False,
                "colbert": False
            }
        })
        headers = {'Content-Type': 'application/json'}
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(self.url, headers=headers, data=payload)
                response.raise_for_status()
                result = response.json()
                return result['embeddings']['dense_vecs'][0]
            except Exception as e:
                logger.warning(f"Lỗi khi gọi API embedding (lần thử {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    logger.error("Đã hết số lần thử lại. Không thể lấy embedding.")
                    raise




"""Embedder sử dụng VertexAI"""

# from langfuse.decorators import observe
# from utils.log_utils import get_logger
# from typing import List
# from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
# import vertexai
# from google.oauth2.service_account import Credentials

# logger = get_logger(__name__)

# class Embedder:
#     def __init__(
#         self,
#         project: str = "communi-ai",
#         location: str = "asia-southeast1",
#         credentials_path: str = "/home/datpt/project/communi_ai_6061cfee10dd.json",
#         model_name: str = "text-multilingual-embedding-002",
#         task: str = "RETRIEVAL_DOCUMENT",
#         dimensionality: int = 256
#     ) -> None:
#         credentials = Credentials.from_service_account_file(
#             credentials_path,
#             scopes=['https://www.googleapis.com/auth/cloud-platform']
#         )
#         vertexai.init(project=project, location=location, credentials=credentials)
#         self.model = TextEmbeddingModel.from_pretrained(model_name)
#         self.task = task
#         self.dimensionality = dimensionality

#     @observe(name="Embedder")
#     def run(self, text: str) -> List[float]:
#         input_text = TextEmbeddingInput(text, self.task)
#         embedding = self.model.get_embeddings(
#             [input_text],
#             output_dimensionality=self.dimensionality
#         )[0]
#         return embedding.values