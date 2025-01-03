from .__init__ import *
from langfuse.decorators import observe
from utils.log_utils import get_logger
from schemas.api_response_schema import ChatLogicInputData
from .generator import Generator
from datetime import datetime
import pytz
import asyncio
from source.config.env_config import OVERLOAD_MESSAGE
from pydantic import BaseModel, Field, field_validator
from typing import List


# Đặt múi giờ thành múi giờ Việt Nam
timezone = pytz.timezone('Asia/Ho_Chi_Minh')

class ChildPrompts(BaseModel):
   """Model cho prompt con"""
   prompt_id: str = Field(description="Sử dụng Auto Increment")
   analysis: str = Field(description="Đây là nơi bạn viết các phân tích để phục vụ cho việc tạo prompt con")
   content: str = Field(description="Nội dung của prompt con này")
   purpose: str = Field(description="Mục đích của prompt con này")

   @field_validator('prompt_id')
   @classmethod
   def validate_prompt_id(cls, v) -> str:
      if not v.strip():
            raise ValueError('ID của prompt con không được để trống.')
      return v

   @field_validator('analysis')
   @classmethod
   def validate_child_analysis(cls, v) -> str:
      if not v.strip():
            raise ValueError('Phân tích không được để trống.')
      return v


   @field_validator('content')
   @classmethod
   def validate_child_content(cls, v) -> str:
      if not v.strip():
            raise ValueError('Nội dung prompt không được để trống')
      return v

   @field_validator('purpose')
   @classmethod
   def validate_child_purpose(cls, v) -> str:
      if not v.strip():
         raise ValueError('Mục đích không được để trống.')
      return v


class QueryResponse(BaseModel):
   analysis: str = Field(description="Đây là nơi bạn viết các phân tích để phục vụ cho câu trả lời cuối cùng")

   child_prompts: List[ChildPrompts] = Field(description="Các prompt con độc lập, được tạo ra để phục vụ cho việc truy xuất các tài liệu liên quan từ cơ sở dữ liệu vector")
   
   @field_validator('child_prompts')
   @classmethod
   def validate_child_prompts(cls, v) -> List[ChildPrompts]:
      if not isinstance(v, list):
         raise ValueError('Các prompt con phải là một danh sách.')
      if not v:
         raise ValueError('Danh sách các prompt con không được để trống.')
      return v



logger = get_logger(__name__)
system_prompt = """\
# NGÀY VÀ GIỜ
Ngày và giờ hiện tại là {current_time}.

# VAI TRÒ
Bạn là Getfly Pro, trợ lý chuyên nghiệp của Getfly CRM.

# THÔNG TIN VỀ GETFLY CRM
- Getfly CRM là một giải pháp quản lý và chăm sóc khách hàng toàn diện, giúp tối ưu việc chăm sóc khách hàng, hỗ trợ quản lý tương tác giữa các bộ phận Marketing, Sales, CSKH trên cùng một nền tảng.
- Getfly CRM có 2 phiên bản: App và Web

# NHIỆM VỤ: PHÂN TÍCH VÀ PHÂN RÃ ĐẦU VÀO
Suy nghĩ thật kĩ và thực hiện theo từng bước dưới đây:
1. Phân tích bối cảnh trò chuyện:
   - Thứ tự ưu tiên: Đầu vào của người dùng > Lịch sử trò chuyện > Tóm tắt lịch sử trò chuyện
   - Đánh giá từ nhiều góc độ
   - Xác định các thực thể, mệnh đề, các mối quan hệ, và ý định chính
   - Loại bỏ thông tin dư thừa, tập trung vào nội dung chính và ý định của người dùng
2. Từ phân tích trên, hãy tạo ra các prompt con liên quan và giúp làm rõ các khía cạnh khác nhau của đầu vào người dùng
   - Phân tích ý định tiềm ẩn
   - Tách biệt các thành phần logic
   - Đảm bảo tính độc lập của từng prompt con, hạn chế sử dụng ngữ cảnh trước đó nếu không cần thiết

# BỐI CẢNH TRÒ CHUYỆN:
Tóm tắt lịch sử trò chuyện:
```
<summary history>
{summary_history}
</summary_history>
```

Lịch sử trò chuyện:
```
<chat history>
{chat_history}
</chat history>
```

Đầu vào của người dùng:
```
<user's input>
{question}
</user's input>
```
"""




class MultiQuery:
   def __init__(
      self,
      generator: Generator,
      max_retries: int = 20,
      retry_delay: float = 2.0
   ) -> None:
      self.generator = generator
      self.max_retries = max_retries
      self.retry_delay = retry_delay

   @observe(name="MultiQuery")
   async def run(self, user_data: ChatLogicInputData, question: str) -> str:
      if len(user_data.histories) < 5:
         taken_messages = user_data.histories  # Lấy tất cả nếu ít hơn 5
      else:
         taken_messages = user_data.histories[-5:-1]
      # Giả sử taken_messages là danh sách các tin nhắn trong chat history
      chat_history: str = "\n".join(map(lambda message: f"{message.role}: {message.content}", taken_messages))
      current_time = datetime.now(timezone).strftime("%A, %Y-%m-%d %H:%M:%S")
      summary_history: str = user_data.summary


      for attempt in range(self.max_retries):
         try:
            response = await self.generator.run(
                     prompt = system_prompt.format(
                        current_time=current_time,
                        summary_history=summary_history,
                        chat_history=chat_history, 
                        question=question,
                        ),
                     temperature = 0.2,
                     response_model=QueryResponse,
            )
            result = {
               "analysis": response.analysis,
               "child_prompt_list": [p.content for p in response.child_prompts],
            }

            return result
         
         
         except Exception as e:
            if attempt < self.max_retries - 1:
               logger.warning(f"Lỗi khi gọi Enrichment (lần thử {attempt + 1}/{self.max_retries}): {str(e)}")
               await asyncio.sleep(self.retry_delay * (2 ** attempt))
            else:
               logger.error("Đã hết số lần thử lại. Không thể tăng cường.")
               return OVERLOAD_MESSAGE