from langfuse.decorators import observe
from utils.log_utils import get_logger
from .generator import Generator
import asyncio
from source.config.env_config import OVERLOAD_MESSAGE
from pydantic import BaseModel, Field
import traceback




class Language(BaseModel):
   reasoning: str = Field(description="Đây là nơi bạn giải thích vì sao bạn chọn ngôn ngữ này")
   language: str = Field(description="Đây là ngôn ngữ của đầu vào người dùng")



logger = get_logger(__name__)
system_prompt = """\
# Nhiệm vụ
- Hãy xác định ngôn ngữ của đầu vào người dùng và trả lời bằng tiếng Việt (Ví dụ: Tiếng Anh, Tiếng Bồ Đào Nha, Tiếng Trung, Tiếng Việt,...)
- Nếu không xác định được ngôn ngữ thì trả về language = "Tiếng Anh"

# Đầu vào của người dùng sẽ được cung cấp dưới đây, được bao quanh bởi dấu ba ngoặc kép:
```
{question}
```
"""




class DetectLanguage:
   def __init__(
      self,
      generator: Generator,
      max_retries: int = 20,
      retry_delay: float = 2.0
   ) -> None:
      self.generator = generator
      self.max_retries = max_retries
      self.retry_delay = retry_delay

   @observe(name="DetectLanguage")
   async def run(self, question: str) -> str:
      for attempt in range(self.max_retries):
         try:
            response = await self.generator.run(
                     prompt = system_prompt.format(
                        question=question,
                        ),
                     temperature = 0.2,
                     response_model=Language,
            )
            result = {
               "reasoning": response.reasoning,
               "language": response.language,
            }
            return result

         except Exception as e:
            logger.warning(f"Lỗi khi gọi DetectLanguage (lần thử {attempt + 1}/{self.max_retries}): {str(e)}")
            logger.error(traceback.format_exc())
            if attempt < self.max_retries - 1:
               await asyncio.sleep(self.retry_delay * (2 ** attempt))
            else:
               logger.error("Đã hết số lần thử lại. Không thể tăng cường.")
               return OVERLOAD_MESSAGE