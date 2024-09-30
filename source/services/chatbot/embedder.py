from langfuse.decorators import observe
from utils.log_utils import get_logger
from openai import OpenAI
from typing import List, Optional
import os

logger = get_logger(__name__)


class Embedder:
    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: str = os.getenv("OPENAI_API_KEY"),
        base_url: Optional[str] = None,
    ) -> None:
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    @observe(name="Embedder")
    def run(self, text: str) -> List[float]:
        response = self.client.embeddings.create(model=self.model, input=text)
        return response.data[0].embedding
