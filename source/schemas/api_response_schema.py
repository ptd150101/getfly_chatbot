import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pydantic import BaseModel, Extra
from typing import List, Literal, Optional, Dict
from enum import Enum
from utils.exception_handler import SUCCESS, ChatbotServiceException
from utils.log_utils import get_logger
from queue import *
logger = get_logger(__name__)
DEFAULT_VERSION = 1
DEFAULT_EVENT = ""


class Status(BaseModel):
    code: int
    message: str = ""

# Ingest Flow


class IngestData(BaseModel):
    user_id: Optional[str] = None
    bot_id: str = ""
    action: Literal["new", "update", ""] = ""
    language: Literal["en", "cs", "es"] = "en"
    # Default code must match with SUCCESS code in exception_handler.py
    status: Status = Status(code=200, message="OK")


# Chat Logic Flow
class ChatMessageRole(str, Enum):
    ASSISTANT = "assistant"
    USER = "user"
    PREVIOUS_SUMMARY_HISTORY = "previous_summary_history"


class ChatMessage(BaseModel):
    role: ChatMessageRole
    content: str = ""
    timestamp: Optional[int] = None


class ChatLogicInputData(BaseModel, extra=Extra.forbid):
    user_id: Optional[str] = None
    user_name: str = ""
    thread_id: Optional[str] = None
    model: str = ""
    content: str = ""
    histories: List[ChatMessage] = []
    summary: str = ""
    language: str = ""
    timestamp: Optional[int] = None
    metadata: Dict = {}


class ChatLogicRequest(BaseModel):
    data: ChatLogicInputData


class ChatLogicOutputData(BaseModel):
    content: List[Dict] = []
    timestamp: Optional[int] = None
    status: Status = Status(code=200, message="OK")
    metadata: Dict = {}
    summary_history: str = ""


class ChatLogicResponse(BaseModel):
    data: ChatLogicOutputData


def make_response(
    api_code,
    content=None,
    log=False,
    summary_history=None
):
    # if only api_code, get message from mapping
    message = ChatbotServiceException(api_code).result["message"]

    if log is True and message is not None:
        if api_code == SUCCESS:
            logger.info(message)
        else:
            logger.exception(message)
    status = Status(code=api_code, message=message)

    if content is None:
        return ChatLogicResponse(
            data=ChatLogicOutputData(
                status=status,
                summary_history=summary_history
            )
        )
    else:
        return ChatLogicResponse(
            data=ChatLogicOutputData(
                status=status,
                content=content,
                summary_history=summary_history
            )
        )



####################################################################
class PhoneChatInput(BaseModel):
    user_id: Optional[str] = None
    model: str = "gemini-pro"
    content: str = ""
    histories: List[ChatMessage] = []
    phone_number: str = ""

class PhoneChatOutput(BaseModel):
    content: str = ""
    phone_number: str = ""
    status: Status = Status(code=200, message="OK")
class PhoneChatOutputError(BaseModel):
    content: str = ""
    phone_number: str = ""
    status: Status = Status(code=-502, message="Error")