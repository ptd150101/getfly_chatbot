from .__init__ import *
from langfuse.decorators import observe
from utils.log_utils import get_logger
from .generator import Generator
import pytz
import asyncio
# Đặt múi giờ thành múi giờ Việt Nam
timezone = pytz.timezone('Asia/Ho_Chi_Minh')


logger = get_logger(__name__)
system_prompt = """\
# INSTRUCTION
- You are an expert translator from {input_language} to {output_language} with over 20 years of experience in diverse areas.
- You are fluent in {output_language} and are also a native {input_language} speaker.
- You deeply understand the nuances of both languages and are familiar with the common expressions and syntax of the {output_language} language.
- Your translations are always natural and accurate.
- Ensure that all proper nouns (e.g., location names, times, personal names) are correct and precise.
- Here are examples of the translation process:
    1. Vietnamese Text: "Thành phố Hà Nội, ngày 20 tháng 7 năm 2021, bà Lê Thị B đã tham gia hội nghị quốc tế về công nghệ thông tin."
    English Translation: "Hanoi, July 20, 2021, Mrs. Le Thi B attended the international conference on information technology."
    2. Vietnamese Text: "Đà Nẵng, vào lúc 15:00 ngày 10 tháng 8 năm 2020, Công ty XYZ đã công bố một sản phẩm mới."
    English Translation: "Da Nang, at 3:00 PM on August 10, 2020, XYZ Company announced a new product."
    3. Vietnamese Text: "Ngày 1 tháng 1 năm 2022, ông Trần Văn C đã tham dự lễ khai trương của nhà hàng Ẩm Thực Việt tại TP.HCM."
    English Translation: "On January 1, 2022, Mr. Tran Van C attended the grand opening of Vietnamese Cuisine Restaurant in HCMC."


# INPUT:
Vietnamese Text
```
{content}
```

# OUTPUT
[Here is your translation. No further explanation]
"""





class Translate:
   def __init__(
      self,
      generator: Generator,
      max_retries: int = 10,
      retry_delay: float = 2.0
   ) -> None:
      self.generator = generator
      self.max_retries = max_retries
      self.retry_delay = retry_delay
   @observe(name="Translate")
   async def run(self, input_language, output_language, content: str) -> str:
      for attempt in range(self.max_retries):
         try:
            text = await self.generator.run(
               prompt=system_prompt.format(input_language=input_language,
                                          output_language=output_language,
                                          content = content
                                          ),
               temperature=0.1
            )

            return text.strip('```').strip() if text.startswith('```') else text.strip() 
         except Exception as e:
            logger.warning(f"Lỗi khi gọi Enrichment (lần thử {attempt + 1}/{self.max_retries}): {str(e)}")
            if attempt < self.max_retries - 1:
               await asyncio.sleep(self.retry_delay)
            else:
               logger.error("Đã hết số lần thử lại. Không thể tăng cường.")
               return "False"