
from pydantic import BaseModel, Field
from typing import Literal, List

DEFAULT_VERSION = 1
DEFAULT_EVENT = ""

class IngestData(BaseModel):
    type: Literal["pdf", "website","textfile"]
    file: str 

class RequestData(BaseModel):
    bot_id: str = Field(..., min_length=1, default_factory=str)
    language: Literal["en", "cs", "es"] = "en"
    action: Literal["new", "update"]
    content: List[IngestData] = Field(..., min_length=1, default_factory=list)

class IngestRequest(BaseModel):
    version: int = DEFAULT_VERSION
    event: str = DEFAULT_EVENT
    request_data: RequestData