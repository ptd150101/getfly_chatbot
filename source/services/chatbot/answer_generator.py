from .__init__ import *
from utils.log_utils import get_logger
from langfuse.decorators import observe
from schemas.api_response_schema import ChatMessage
from typing import List
from schemas.document import Document
from services.chatbot.chat_generator import ChatGenerator
from datetime import datetime
import pytz
import requests
import re
import asyncio
from source.config.setting_bot import GETFLY_BOT_SETTINGS
# Đặt múi giờ thành múi giờ Việt Nam
timezone = pytz.timezone('Asia/Ho_Chi_Minh')
logger = get_logger(__name__)



system_prompt_template_with_context = """
# NGÀY VÀ GIỜ
Ngày và giờ hiện tại là {current_time}.

# VAI TRÒ CỦA BẠN
- Tên của bạn là Getfly Pro.
- Bạn là trợ lý hữu ích của Getfly.
- Bạn là chuyên gia xuất sắc trong việc hiểu ý định của người dùng và trọng tâm của đầu vào người dùng, và cung cấp câu trả lời tối ưu nhất cho nhu cầu của người dùng từ các tài liệu bạn được cung cấp.

# HƯỚNG DẪN
Nhiệm vụ của bạn là trả lời đầu vào của người dùng bằng cách sử dụng các văn bản sau được truy xuất trong ngữ cảnh giới hạn bởi các thẻ XML.

```
<RETRIEVED CONTEXT>
Ngữ cảnh truy xuất:
{context}
</RETRIEVED CONTEXT>
```

# RÀNG BUỘC
1. Getfly Pro không thể mở URL, liên kết hoặc video. Nếu người dùng yêu cầu thông tin từ các nguồn này, hãy yêu cầu họ dán văn bản hoặc hình ảnh liên quan trực tiếp vào cuộc trò chuyện.

2. Nghĩ sâu sắc và phân tích nhiều lần về đầu vào, câu trả lời trước đó của người dùng và lịch sử tóm tắt:

3. Chọn nội dung liên quan nhất (nội dung chính liên quan trực tiếp đến đầu vào của người dùng) từ ngữ cảnh truy xuất và sử dụng nó để tạo câu trả lời.

4. Tạo câu trả lời ngắn gọn, logic. Khi tạo câu trả lời, không chỉ liệt kê các lựa chọn của bạn, mà hãy sắp xếp chúng trong ngữ cảnh để chúng trở thành đoạn văn có dòng chảy tự nhiên.

5. Nếu ngữ cảnh truy xuất có nội dung không liên quan đến đầu vào của người dùng, bạn phải trả lời là: "Xin lỗi, tôi không tìm thấy câu trả lời cho câu hỏi của bạn. Vui lòng mô tả câu hỏi kĩ hơn hoặc kết nối với bộ phận CSKH."

6. Sử dụng tối thiểu bốn câu và tối đa tám câu để trả lời. Giữ câu trả lời ngắn gọn nhưng logic/tự nhiên/sâu sắc.

{open_question_instruction}

8. Luôn luôn trích dẫn URL gốc của các đoạn văn trong ngữ cảnh truy xuất mà bạn đã sử dụng để trả lời đầu vào của người dùng.

9. Nghĩ sâu sắc và phân tích nhiều lần về đầu vào của người dùng, lịch sử trò chuyện và tóm tắt lịch sử trò chuyện:
- Bạn phải hiểu ý định của đầu vào của họ và cung cấp câu trả lời phù hợp nhất.

- Hãy tự hỏi "tại sao" để hiểu ngữ cảnh của đầu vào của người dùng và lý do tại sao người dùng hỏi điều đó, suy ngẫm về nó và cung cấp câu trả lời phù hợp dựa trên những gì bạn hiểu.

- Hãy suy nghĩ từng bước một để đưa ra câu trả lời thật chính xác.


# ĐỊNH DẠNG ĐẦU VÀO
- Lịch sử trò chuyện:
```
{pqa}
```

- Tóm tắt lịch sử trò chuyện:
```
{summary_history}
```

- Đầu vào gốc của người dùng
```
{original_query}
```

- Đầu vào của người dùng đã được viết lại
```
{transform_query}
```


# ĐỊNH DẠNG CÂU TRẢ LỜI
- Câu trả lời của bạn luôn luôn bao gồm 2 phần được tách riêng biệt:
    1. Phần trả lời: Phần này chỉ bao gồm câu trả lời của bạn (Không đưa link vào phần này)
    2. Phần xem thêm: Phần này bao gồm link của các đoạn văn bạn sử dụng để trả lời
- {open_question_format}

```
[Your Answer Here]
```

Xem thêm:
```
Link gốc của các đoạn văn bạn đã sử dụng để trả lời ở dạng bullet (nếu có)
```

# VÍ DỤ VỀ ĐỊNH DẠNG CÂU TRẢ LỜI
- Ví dụ 1:
Nếu phải dựa vào url nào đó để trả lời:
```
[Your Answer Here]
```

Xem thêm:
```
- url_1
- url_2
...
```

- Ví dụ 2:
Nếu không cần dựa vào url nào để trả lời:
```
[Your Answer Here]
```
"""


system_prompt_template_no_context = """
# NGÀY VÀ GIỜ
Ngày và giờ hiện tại là {current_time}.

# Vai trò của bạn
- Tên của bạn là Getfly Pro.
- Bạn là trợ lý hữu ích của Getfly.
- Bạn là chuyên gia xuất sắc trong việc hiểu ý định của người dùng và trọng tâm của đầu vào người dùng, và cung cấp câu trả lời tối ưu nhất cho nhu cầu của người dùng từ bối cảnh được cung cấp.

# YÊU CẦU
- CHỈ ĐƯỢC THAM KHẢO BỐI CẢNH ĐƯỢC ĐẶT TRONG THẺ XML <CONTEXT> DƯỚI ĐÂY ĐỂ TRẢ LỜI ĐẦU VÀO CỦA NGƯỜI DÙNG.
- NẾU BỐI CẢNH ĐƯỢC CUNG CẤP KHÔNG ĐỦ DỮ KIỆN ĐỂ TRẢ LỜI ĐẦU VÀO CỦA NGƯỜI DÙNG, ĐỪNG CỐ GẮNG TẠO CÂU TRẢ LỜI. CHỈ CẦN TRẢ LỜI LÀ: "Xin lỗi, tôi không tìm thấy câu trả lời cho câu hỏi của bạn. Vui lòng mô tả câu hỏi kĩ hơn hoặc kết nối với bộ phận CSKH."

<CONTEXT>
# LỊCH SỬ TRÒ CHUYỆN:
```
{pqa}
```

# TÓM TẮT LỊCH SỬ TRÒ CHUYỆN:
```
{summary_history}
```
</CONTEXT>

# ĐẦU VÀO GỐC CỦA NGƯỜI DÙNG
```
{original_query}
```

# ĐẦU VÀO CỦA NGƯỜI DÙNG ĐÃ ĐƯỢC VIẾT LẠI
```
{transform_query}
```

# VÍ DỤ VỀ ĐẦU RA
- Ví dụ 1:
```
USER: Cách quản lý kho? ----> Liên quan đến Getfly CRM
GETFLY PRO: [Câu trả lời của bạn ở đây]
```

- Ví dụ 2:
```
USER: Bạn được ai huẩn luyện? ----> Không liên quan đến Getfly CRM
GETFLY PRO: Xin lỗi, tôi không tìm thấy câu trả lời cho câu hỏi của bạn. Vui lòng mô tả câu hỏi kĩ hơn hoặc kết nối với bộ phận CSKH.
```

- Ví dụ 3:
```
USER: Bạn bao nhiêu tuổi? ----> Không liên quan đến Getfly CRM
GETFLY PRO: Xin lỗi, tôi không tìm thấy câu trả lời cho câu hỏi của bạn. Vui lòng mô tả câu hỏi kĩ hơn hoặc kết nối với bộ phận CSKH.
```
"""


class AnswerGenerator:
    def __init__(
        self,
        chat_generator: ChatGenerator,
        # open_question_mode: str = "auto",
        settings: dict = None
    ) -> None:
        self.chat_generator = chat_generator
        self.settings = settings if settings else GETFLY_BOT_SETTINGS
        self.timezone = pytz.timezone(self.settings["timezone"])
        # self.open_question_mode = open_question_mode


    def run(self, messages: List[ChatMessage], relevant_documents: List[dict], summary_history: str, original_query: str, transform_query: str) -> str:
        if len(relevant_documents) == 0:
            return self.runNoContext(messages=messages, 
                                     summary_history=summary_history,
                                     original_query=original_query,
                                     transform_query=transform_query
                                     )
        return self.runWithContext(messages=messages, 
                                   relevant_documents=relevant_documents, 
                                   summary_history=summary_history,
                                   original_query=original_query,
                                   transform_query=transform_query
                                   )
                                   


    @observe(name="AnswerGeneratorWithContext")
    async def runWithContext(self, messages: List[ChatMessage], relevant_documents: List[dict], summary_history: str, original_query: str, transform_query: str) -> str:
        relevant_documents = [Document(
            id=doc['id'],
            text=doc['text'],
            page_content=doc['page_content'],
            enriched_content=doc['enriched_content'],
            url=doc['url'],
            score=doc.get('score'),
            cross_score=doc.get('cross_score')
        ) for doc in relevant_documents]
        
        open_question_mode = self.settings["open_question_mode"]
        open_question_config = self.settings["open_question_formats"][open_question_mode]
        
        current_time = datetime.now(self.timezone).strftime("%A, %Y-%m-%d %H:%M:%S")
        taken_messages = messages[-5:-1]
        pqa: str = "\n".join(map(lambda message: f"{message.role}: {message.content}", taken_messages))
        def format_document(index, doc):
            doc_start = f"\t<Document {index}>\n"
            url_line = f"\t\tURL: {doc.url}\n" if 'http' in str(doc.url).lower() else ''
            content_line = f"\t\t{doc.page_content}\n"
            doc_end = f"\t</Document {index}>"
            return doc_start + url_line + content_line + doc_end

        context: str = "\n".join(
            format_document(i, doc) 
            for i, doc in enumerate(relevant_documents, 1)
        )



        # Thêm cấu hình Retry
        retry_settings = {
            "max_retries": 20,  # Số lần thử lại tối đa
            "initial_delay": 1,  # Thời gian chờ ban đầu (giây)
            "max_delay": 60,  # Thời gian chờ tối đa (giây)
            "multiplier": 2,  # Hệ số tăng thời gian chờ
        }

        # Thực hiện yêu cầu với Retry
        for attempt in range(retry_settings["max_retries"]):
            try:
                result = await self.chat_generator.run(
                    messages=messages, 
                    system_prompt=system_prompt_template_with_context.format(
                        current_time=current_time, 
                        context=context,
                        pqa=pqa,
                        summary_history=summary_history,
                        transform_query = transform_query,
                        original_query=original_query,
                        open_question_instruction=open_question_config["instruction"],
                        open_question_format=open_question_config["format"]), 
                    temperature=0.2)
                return result.strip('```').strip() if result.startswith('```') else result.strip()
            
            
            
            except Exception as e:
                if attempt < retry_settings["max_retries"] - 1:
                    # Tính toán thời gian chờ với max_delay
                    delay = min(retry_settings["initial_delay"] * (retry_settings["multiplier"] ** attempt), retry_settings["max_delay"])
                    await asyncio.sleep(delay)
                else:
                    raise e

    @observe(name="FormatAnswer") 
    def format_answer(self, answer: str) -> str:
        answer = answer.replace("```", "")
        # Xử lý xuống hàng
        answer = re.sub(r'([.!?])\s{2}', r'\1\n\n\n', answer)
        
        # Xử lý URL trùng nhau trong phần "Xem thêm"
        if "Xem thêm:" in answer:
            # Tách phần trước và sau "Xem thêm:"
            parts = answer.split("Xem thêm:", 1)
            content = parts[0]
            urls = parts[1]
            
            # Lấy danh sách URL unique
            unique_urls = []
            for url in re.findall(r'- (.*?)(?:\n|$)', urls):
                if url.strip() not in unique_urls:
                    unique_urls.append(url.strip())
            
            # Ghép lại với URLs unique
            answer = content + "Xem thêm:\n" + "\n".join(f"- {url}" for url in unique_urls)
        
        # Xử lý thừa "Câu trả lời của bạn"
        if answer.startswith("Câu trả lời của bạn"):
            answer = answer.replace("Câu trả lời của bạn\n", "", 1)

        return answer.strip('```').strip() if answer.startswith('```') else answer.strip()

   


    @observe(name="AnswerGeneratorNoContext")
    async def runNoContext(self, messages: List[ChatMessage], summary_history: str, original_query: str, transform_query: str) -> str:
        current_time = datetime.now(self.timezone).strftime("%A, %Y-%m-%d %H:%M:%S")
        taken_messages = messages[-5:-1]
        pqa: str = "\n".join(map(lambda message: f"{message.role}: {message.content}", taken_messages))

        # Thêm cấu hình Retry
        retry_settings = {
            "max_retries": 20,  # Số lần thử lại tối đa
            "initial_delay": 1,  # Thời gian chờ ban đầu (giây)
            "max_delay": 60,  # Thời gian chờ tối đa (giây)
            "multiplier": 2,  # Hệ số tăng thời gian chờ
        }

        # Thực hiện yêu cầu với Retry
        for attempt in range(retry_settings["max_retries"]):
            try:
                text = await self.chat_generator.run(
                    messages=messages, 
                    system_prompt=system_prompt_template_no_context.format(
                        summary_history=summary_history, 
                        original_query=original_query,
                        pqa=pqa,
                        transform_query=transform_query,
                        current_time=current_time), 
                    temperature=0.2)
                return text.strip('```').strip() if text.startswith('```') else text.strip()
            except Exception as e:
                if attempt < retry_settings["max_retries"] - 1:
                    # Tính toán thời gian chờ với max_delay
                    delay = min(retry_settings["initial_delay"] * (retry_settings["multiplier"] ** attempt), retry_settings["max_delay"])
                    await asyncio.sleep(delay)
                else:
                    raise e
