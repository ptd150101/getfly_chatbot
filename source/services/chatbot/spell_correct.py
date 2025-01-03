from . import *
from langfuse.decorators import observe
from utils.log_utils import get_logger
from .generator import Generator
import asyncio
from source.config.env_config import OVERLOAD_MESSAGE
from pydantic import BaseModel, Field, field_validator
from enum import Enum



class InputValidation(str, Enum):
   """Enum cho các trạng thái routing của spell check"""
   VALID = "CORRECT"
   INVALID = "UNCORRECT"


class InputAnalysis(BaseModel):
   """Model phân tích và sửa lỗi chính tả trong câu hỏi của người dùng"""
   analysis: str = Field(description="Đây là nơi bạn viết các phân tích dùng để phục vụ cho câu trả lời")

   validation: InputValidation = Field(
      description="CORRECT nếu input có ý nghĩa, UNCORRECT nếu input không có ý nghĩa"
   )
   corrected_text: str = Field(
      description="Văn bản đã được sửa lỗi chính tả và lỗi gõ phím (giữ nguyên văn bản gốc nếu validation là UNCORRECT)"
   )

   @field_validator('analysis')
   @classmethod
   def validate_analysis(cls, v, values) -> str:
      v = v.strip()
      # Nếu validation là INVALID, không cần kiểm tra corrected_text
      if 'validation' in values.data and values.data['validation'] == InputValidation.INVALID:
         return v
      # Nếu validation là VALID, corrected_text không được rỗng
      if not v:
         raise ValueError('Văn bản đã sửa không được để trống khi validation là CORRECT')
      return v


   @field_validator('corrected_text')
   @classmethod
   def validate_corrected_text(cls, v, values) -> str:
      v = v.strip()
      # Nếu validation là INVALID, không cần kiểm tra corrected_text
      if 'validation' in values.data and values.data['validation'] == InputValidation.INVALID:
         return v
      # Nếu validation là VALID, corrected_text không được rỗng
      if not v:
         raise ValueError('Văn bản đã sửa không được để trống khi validation là CORRECT')
      return v
   @field_validator('validation')
   @classmethod
   def validate_validation(cls, v) -> InputValidation:
      if v not in InputValidation:
         raise ValueError('Giá trị của validation phải là VALID hoặc INVALID')
      return v
   
   

logger = get_logger(__name__)
system_prompt = """\
# NHIỆM VỤ
Bạn có 2 nhiệm vụ chính:
## Nhiệm vụ 1:
   - Nếu đầu vào của người dùng là một văn bản nhập linh tinh (nội dung trông không có ngữ nghĩa gì), hãy trả về ROUTING là UNCORRECT.
   - Các trường hợp còn lại hãy trả về ROUTING là CORRECT.
Chỉ thực hiện Nhiệm Vụ 2 nếu Nhiệm Vụ 1 trả về “ROUTING: CORRECT”.

## Nhiệm vụ 2:
   - Phát hiện và sửa các lỗi chính tả và lỗi gõ phím (Telex, VNI),... trong văn bản tiếng Việt và sửa lại.

# YÊU CẦU:
   1. GIỮ NGUYÊN TỪNG CÂU CHỮ CỦA VĂN BẢN GỐC, CHỈ CẦN SỬA LẠI CHO ĐÚNG.
   2. ĐỪNG cố gắng sửa lỗi chính tả quá mức cần thiết.
   3. Chỉ thực hiện nhiệm vụ đã được giao, không thực hiện những việc không liên quan.
   4. Phải dựa vào toàn bộ dữ liệu đầu vào được cung cấp để làm căn cứ sửa lỗi.

# Các lỗi gõ phím phổ biến cần phải sửa bao gồm nhưng không giới hạn ở:
   * Telex: dd => đ, w => ư, ow => ơ, aa => â,...

# VÍ DỤ
   - "Tôi yeu Viet Nam." => "Tôi yêu Việt Nam."
   - "Ban ddax an com chua?" => "Bạn đã ăn cơm chưa?"
   - "Quran ly kho" => "Quản lý kho"


# Đầu vào của người dùng:
```
{question}
```
"""




class InputValidator:
   def __init__(
      self,
      generator: Generator,
      max_retries: int = 20,
      retry_delay: float = 2.0
   ) -> None:
      self.generator = generator
      self.max_retries = max_retries
      self.retry_delay = retry_delay

   @observe(name="InputValidator")
   async def run(self, question: str) -> str:
      for attempt in range(self.max_retries):
         try:
            response = await self.generator.run(
                     prompt = system_prompt.format(
                        question=question,
                        ),
                     temperature = 0.2,
                     response_model=InputAnalysis,
            )
            return {
               "analysis": response.analysis,
               "routing": response.validation.value,
               "correct_query": response.corrected_text if response.validation == InputValidation.VALID else question
            }
         
         
         except Exception as e:
               if attempt < self.max_retries - 1:
                  logger.warning(f"Lỗi khi kiểm tra đầu vào (lần thử {attempt + 1}/{self.max_retries}): {str(e)}")
                  await asyncio.sleep(self.retry_delay * (2 ** attempt))
               else:
                  logger.error("Đã hết số lần thử lại. Không thể kiểm tra đầu vào.")
                  return OVERLOAD_MESSAGE