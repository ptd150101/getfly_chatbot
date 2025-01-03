from langfuse.decorators import observe
from utils.log_utils import get_logger
from schemas.api_response_schema import ChatMessage
from typing import List
from .generator import Generator
import asyncio
from pydantic import BaseModel, Field, field_validator



class SummaryResponse(BaseModel):
    """Model cho phản hồi tóm tắt"""
    analysis: str = Field(
        description="Đây là nơi bạn viết các phân tích về logic tóm tắt cuộc trò chuyện"
    )
    summary_history: str = Field(
        description="Nội dung tóm tắt cuộc trò chuyện"
    )


    @field_validator('analysis')
    @classmethod
    def validate_analysis(cls, v) -> str:
        if not v.strip():
                raise ValueError('Phân tích không được để trống')
        return v


    @field_validator('summary_history')
    @classmethod
    def validate_summary_history(cls, v) -> str:
        if not v.strip():
                raise ValueError('Nội dung tóm tắt cuộc trò chuyện không được để trống')
        return v


logger = get_logger(__name__)

system_prompt = """\
# NHIỆM VỤ
Bạn là một người tóm tắt cuộc trò chuyện.
Nhiệm vụ của bạn là duy trì một bản tóm tắt đầy đủ nội dung, có liên quan về lịch sử đối thoại giữa người dùng và trợ lý.
Hãy tuân theo các quy tắc sau:
1. Bản tóm tắt trước: {previous_summary}
2. Các tin nhắn mới để tích hợp:
    USER: {user_message}
    GETFLY PRO: {assistant_message}
3. Tóm tắt toan bộ nội dung cuộc trò chuyện bằng cách:
- Chỉ giữ lại những điểm chính, quyết định và ngữ cảnh cần thiết cho các phản hồi trong tương lai
- Ưu tiên các tương tác gần đây trong khi bảo tồn ngữ cảnh thiết yếu trước đó
- Tập trung vào các mục hành động và các mục tiêu chính của người dùng
- Loại bỏ các câu xã giao và đối thoại thường lệ (câu khen, câu chào,...)
4. Sử dụng tiếng việt trong câu trả lời
"""


class Summary:
    def __init__(
        self,
        generator: Generator,
        max_retries: int = 20,
        retry_delay: float = 2.0
    ) -> None:
        self.generator = generator
        self.max_retries = max_retries
        self.retry_delay = retry_delay



    @observe(name="Summary")
    async def run(self, messages: List[ChatMessage], previous_summary: str, assistant_message: str) -> str:
        user_message = messages[-1].content
        for attempt in range(self.max_retries):
            try:
                text = await self.generator.run(
                            prompt = system_prompt.format(
                                previous_summary=previous_summary,
                                user_message=user_message,
                                assistant_message=assistant_message
                            ),
                            temperature = 0.2,
                            response_model = SummaryResponse
                )
                result = {
                    "analysis": text.analysis,
                    "summary_history": text.summary_history,
                }
                return result.get("summary_history", "")
            
            
            except Exception as e:
                logger.warning(f"Lỗi khi gọi Summary (lần thử {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error("Đã hết số lần thử lại. Không thể tóm tắt.")
                    return "False"