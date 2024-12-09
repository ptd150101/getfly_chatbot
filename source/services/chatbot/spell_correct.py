from .__init__ import *
from langfuse.decorators import observe
from utils.log_utils import get_logger
from .generator import Generator
import pytz
import asyncio
from source.config.env_config import OVERLOAD_MESSSAGE
from schemas.api_response_schema import ChatLogicInputData

import json
# Đặt múi giờ thành múi giờ Việt Nam
timezone = pytz.timezone('Asia/Ho_Chi_Minh')


logger = get_logger(__name__)
system_prompt = """\
# NHIỆM VỤ
Bạn có 2 nhiệm vụ chính:
- Nhiệm vụ 1:
   - Nếu đầu vào của người dùng là một văn bản nhập linh tinh (nội dung trông không có ngữ nghĩa gì), hãy trả về ROUTING là UNCORRECT.
   - Các trường hợp còn lại hãy trả về ROUTING là CORRECT.

Nếu nhiệm vụ 1 trả về CORRECT thì mới thực hiện nhiệm vụ 2
- Nhiệm vụ 2: Phát hiện và sửa các lỗi chính tả và lỗi gõ phím (Telex, VNI),... trong văn bản tiếng Việt và sửa lại.


# YÊU CẦU:
   1. GIỮ NGUYÊN TỪNG CÂU CHỮ CỦA VĂN BẢN GỐC, CHỈ CẦN SỬA LẠI CHO ĐÚNG.
   2. ĐỪNG cố gắng sửa lỗi chính tả quá mức cần thiết.
   3. Nhớ kĩ nhiệm vụ của bạn là gì, đừng cố làm những việc không liên quan tới nhiệm vụ.
   4. Phải dựa vào toàn bộ dữ liệu đầu vào được cung cấp 

# Các lỗi gõ phím phổ biến cần phải sửa bao gồm nhưng không giới hạn ở:
* Telex: dd => đ, w => ư, ow => ơ, aa => â,...
* VNI: dd => đ, w => ư, ow => ơ,...

# VÍ DỤ
- "Tôi yeu Viet Nam." => "Tôi yêu Việt Nam."
- "Ban ddax an com chua?" => "Bạn đã ăn cơm chưa?"
- "Quran ly kho" => "Quản lý kho"


# DỮ LIỆU ĐẦU VÀO
Đầu vào của người dùng:
```
<user's input>
{question}
</user's input>
```


# ĐỊNH DẠNG ĐẦU RA (TUÂN THỦ CHÍNH XÁC)
Câu trả lời của bạn luôn bao gồm hai phần (Hai khối phần tử):
<ROUTING>
CORRECT hoặc UNCORRECT
</ROUTING>
<CORRECTED_TEXT>
Đây là nơi bạn chỉ xuất ra văn bản đã được sửa lỗi chính tả, lỗi đánh máy sai,... Không thêm bất kỳ bình luận nào.
</CORRECTED_TEXT>
"""





class SpellCorrect:
   def __init__(
      self,
      generator: Generator,
      max_retries: int = 20,
      retry_delay: float = 2.0
   ) -> None:
      self.generator = generator
      self.max_retries = max_retries
      self.retry_delay = retry_delay

   @observe(name="SpellCorrect")
   async def run(self, user_data: ChatLogicInputData, question: str) -> str:
      taken_messages = user_data.histories[-5:-1]
      # Giả sử taken_messages là danh sách các tin nhắn trong chat history
      chat_history: str = "\n".join(map(lambda message: f"{message.role}: {message.content}", taken_messages))
      summary_history: str = user_data.summary
      
      
      for attempt in range(self.max_retries):
         try:
            text = await self.generator.run(
               prompt=system_prompt.format(summary_history=summary_history,
                                           chat_history=chat_history,
                                           question=question
                                           ),
               temperature=0.1
            )
            correct_query = text.split("<CORRECTED_TEXT>")[1].split("</CORRECTED_TEXT>")[0].strip()
            routing = text.split("<ROUTING>")[1].split("</ROUTING>")[0].strip()

            correct_query = correct_query.strip('```').strip() if correct_query.startswith('```') else correct_query.strip() 
            routing = routing.strip('```').strip() if routing.startswith('```') else routing.strip() 
         
            return json.dumps({
               "correct_query": correct_query,
               "routing": routing
               })
         
         except (asyncio.TimeoutError, ConnectionError, Exception) as e:
            if attempt < self.max_retries - 1:
               logger.warning(f"Lỗi khi gọi Enrichment (lần thử {attempt + 1}/{self.max_retries}): {str(e)}")
               await asyncio.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
            else:
               logger.error("Đã hết số lần thử lại. Không thể tăng cường.")
               return OVERLOAD_MESSSAGE