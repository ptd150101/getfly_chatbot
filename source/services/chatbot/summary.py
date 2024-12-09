from langfuse.decorators import observe
from utils.log_utils import get_logger
from schemas.api_response_schema import ChatLogicInputData, ChatMessage
from typing import List
from .generator import Generator
import asyncio
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

# ĐỊNH DẠNG ĐẦU RA
SUMMARY: [Your summary here]
Không bao gồm bất kỳ nhận xét hay giải thích nào về quá trình xử lý. Chỉ cần xuất ra bản tóm tắt.
"""


class Summary:
    def __init__(
        self,
        generator: Generator,
        max_retries: int = 10,
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
                    prompt=system_prompt.format(previous_summary=previous_summary,
                                                user_message=user_message,
                                                assistant_message=assistant_message, 
                                                ),
                    temperature=0.1
                )
                if "SUMMARY:" in text:
                    text = text.split("SUMMARY:")[-1].strip()
                return text.strip('```').strip() if text.startswith('```') else text.strip()
            except Exception as e:
                logger.warning(f"Lỗi khi gọi Summary (lần thử {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error("Đã hết số lần thử lại. Không thể tóm tắt.")
                    return "False"