from .__init__ import *
from langfuse.decorators import observe
from utils.log_utils import get_logger
from .generator import Generator
import asyncio
from source.config.env_config import OVERLOAD_MESSAGE
from pydantic import BaseModel, Field
import traceback
from enum import Enum 


class PlatformEnum(str, Enum):
   APP = "App Getfly"
   WEBSITE = "Phiên bản web"
   OTHER = "Other"

class Platform(BaseModel):
   analysis: str = Field(description="Đây là nơi bạn viết các phân tích dùng để phục vụ cho câu trả lời")
   platform: PlatformEnum = Field()



logger = get_logger(__name__)
system_prompt = """\
# VAI TRÒ
Bạn là Getfly Pro, trợ lý chuyên nghiệp của Getfly CRM.

# THÔNG TIN VỀ GETFLY CRM
Getfly CRM là một giải pháp quản lý và chăm sóc khách hàng toàn diện, giúp tối ưu việc chăm sóc khách hàng, hỗ trợ quản lý tương tác giữa các bộ phận Marketing, Sales, CSKH trên cùng một nền tảng.

# NHIỆM VỤ
Suy nghĩ thật kĩ và thực hiện từng bước theo flow Mermaid dưới đây:
   A[Bắt đầu] --> B[Phân tích đầu vào của người dùng, từ đó nhận diện xem người dùng muốn đề cập đến nền tảng nào?]
   B -->|App Getfly| C[Trả về context_string = App Getfly]
   B -->|Phiên bản Web| D[Trả về context_string = Phiên bản web]

Nếu không đủ dữ kiện để trả lời, thì trả về context_string là Other

# ĐẦU VÀO CỦA NGƯỜI DÙNG
```
{question}
```
"""




class DetectPlatform:
   def __init__(
      self,
      generator: Generator,
      max_retries: int = 20,
      retry_delay: float = 2.0
   ) -> None:
      self.generator = generator
      self.max_retries = max_retries
      self.retry_delay = retry_delay

   @observe(name="DetectPlatform")
   async def run(self, question: str) -> str:
      for attempt in range(self.max_retries):
         try:
            response = await self.generator.run(
                     prompt = system_prompt.format(
                        question=question,
                        ),
                     temperature = 0.2,
                     response_model=Platform,
            )
            result = {
               "analysis": response.analysis,
               "platform": response.platform.value,
            }
            return result

         except Exception as e:
            logger.warning(f"Lỗi khi gọi Enrichment (lần thử {attempt + 1}/{self.max_retries}): {str(e)}")
            logger.error(traceback.format_exc())
            if attempt < self.max_retries - 1:
               await asyncio.sleep(self.retry_delay * (2 ** attempt))
            else:
               logger.error("Đã hết số lần thử lại. Không thể tăng cường.")
               return OVERLOAD_MESSAGE