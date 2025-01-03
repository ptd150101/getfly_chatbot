import sys
import os

# Thêm thư mục gốc vào sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))
from model_database.outline_database import Embedding, SessionLocal


from utils.log_utils import get_logger
from langfuse.decorators import observe
from schemas.api_response_schema import ChatMessage
from typing import List
from schemas.document import RelevantDocument
from services.chatbot.chat_generator import ChatGenerator
from datetime import datetime
import pytz
import re
from pydantic import BaseModel, Field, field_validator
from typing import List
import asyncio
from source.config.setting_bot import GETFLY_BOT_SETTINGS



# Đặt múi giờ thành múi giờ Việt Nam
timezone = pytz.timezone('Asia/Ho_Chi_Minh')
logger = get_logger(__name__)


class References(BaseModel):
    """Model định dạng thông tin tham chiếu"""
    chunk_id: str = Field(description="ID của chunk tài liệu đã được sử dụng để trả lời")
    score: float = Field(default=0.0, description="Điểm số đánh giá mức độ liên quan của chunk tài liệu")
    
    
    def dict(self):
        return {
            "chunk_id": self.chunk_id,
            "score": self.score
        }



class ChatResponseWithContext(BaseModel):
    """Model định dạng câu trả lời của AI"""
    context_analysis: str = Field(
        description="Phân tích tài liệu được cung cấp và bối cảnh trò chuyện"
    )
    is_query_answerable: bool = Field(
        description="Dựa vào tài liệu được cung cấp và bối cảnh trò chuyện, nhận định xem có đủ thông tin để trả lời đầu vào của người dùng hay không?"
    )

    answer: str = Field(
        description="Dựa vào tài liệu được cung cấp và bối cảnh trò chuyện, đưa ra câu trả lời logic, tự nhiên và sâu sắc"
    )
    references: List[References] = Field(
        description="Danh sách các thông tin tham chiếu đã được sử dụng để trả lời (Nếu có)"
    )

    
    @field_validator('context_analysis')
    def check_context_analysis(cls, v):
        if not v.strip():
            raise ValueError('Phân tích ngữ cảnh không được để trống.')
        return v

    @field_validator('is_query_answerable')
    def check_is_query_answerable(cls, v):
        if v is None:
            raise ValueError('Đánh giá tính rõ ràng của đầu vào không được để trống.')
        return v

    @field_validator('answer')
    def check_answer(cls, v):
        if not v.strip():
            raise ValueError('Nội dung câu trả lời không được để trống.')
        return v

    @field_validator('references')
    def check_references(cls, v):
        if not isinstance(v, list) or any(not isinstance(ref, References) for ref in v):
            raise ValueError('References phải là một danh sách các đối tượng References.')
        return v

system_prompt_template_with_context = """
# NGÀY VÀ GIỜ
Ngày và giờ hiện tại là {current_time}.

# VAI TRÒ CỦA BẠN
- Bạn là một nhân viên chăm sóc khách hàng của Getfly. Phong cách của bạn chuyên nghiệp, lịch sự, nhưng vẫn giữ được sự thân thiện và dễ gần.
- Bạn là chuyên gia xuất sắc trong việc hiểu ý định của người dùng và trọng tâm của đầu vào người dùng, và cung cấp câu trả lời tối ưu nhất cho nhu cầu của người dùng từ các tài liệu bạn được cung cấp.

# NHIỆM VỤ
Nhiệm vụ của bạn là trả lời đầu vào của người dùng bằng cách sử dụng tài liệu được cung cấp, được đặt trong thẻ XML <RETRIEVED CONTEXT> dưới đây:
```
TÀI LIỆU ĐƯỢC CUNG CẤP:
<RETRIEVED CONTEXT>
{context}
</RETRIEVED CONTEXT>
```

# PIPELINE
Suy nghĩ thật kĩ và thực hiện từng bước theo flow Mermaid dưới đây:
    A[Bắt đầu] --> C[Dựa vào tài liệu được cung cấp và bối cảnh trò chuyện, nhận định xem có đủ thông tin để trả lời đầu vào của người dùng hay không?]

    C -->|Không đủ thông tin| D[Yêu cầu người dùng làm rõ thêm]
    
    C -->|Đủ thông tin| E[Phân tích tài liệu được cung cấp cùng với các nội dung dưới đây:
    - Đầu vào của người dùng
    - Lịch sử trò chuyện
    - Bản tóm tắt lịch sử trò chuyện]
    
    D --> I[Gửi câu trả lời]
    
    E --> F[Chọn lọc ra những nội dung liên quan nhất đến đầu vào của người dùng]
    
    F --> G[Tạo câu trả lời:
    - Logic
    - Tự nhiên
    - Sâu sắc
    - Không sử dụng câu hỏi mở
    - Dùng ít nhất 4 câu
    - Trong câu trả lời không trích dẫn Chunk ID
    - Dùng Markdown để định dạng câu trả lời
    - Sử dụng ngôn ngữ giống ngôn ngữ đầu vào của người dùng]
    
    G --> H[Trích dẫn Chunk ID của các tài liệu đã sử dụng để trả lời cùng với điểm số liên quan (từ 1-10)]
    
    H --> I[Gửi câu trả lời]
    
    I --> J[Kết thúc]

# BỐI CẢNH TRÒ CHUYỆN
1. Lịch sử trò chuyện:
```
{pqa}
```

2. Tóm tắt lịch sử trò chuyện:
```
{summary_history}
```

3. Đầu vào của người dùng
```
{original_query}
```
"""




class ChatResponseWithNoContext(BaseModel):
    """Model định dạng câu trả lời của AI"""
    context_analysis: str = Field(
        description="Phân tích bối cảnh trò chuyện"
    )
    is_query_answerable: bool = Field(
        default=None,
        description="Dựa vào bối cảnh trò chuyện, nhận định xem có đủ thông tin để trả lời đầu vào của người dùng hay không?"
    )
    answer: str = Field(
        description="Dựa vào bối cảnh trò chuyện, đưa ra câu trả lời logic, tự nhiên và sâu sắc"
    )
    @field_validator('context_analysis')
    def check_context_analysis(cls, v):
        if not v.strip():
            raise ValueError('Phân tích ngữ cảnh không được để trống.')
        return v

    @field_validator('is_query_answerable')
    def check_is_query_answerable(cls, v):
        if v is None:
            raise ValueError('Đánh giá tính rõ ràng của đầu vào không được để trống.')
        return v

    @field_validator('answer')
    def check_answer(cls, v):
        if not v.strip():
            raise ValueError('Nội dung câu trả lời không được để trống.')
        return v



system_prompt_template_no_context = """\
# NGÀY VÀ GIỜ
Ngày và giờ hiện tại là {current_time}.

# THÔNG TIN VỀ GETFLY
Getfly CRM là một giải pháp quản lý khách hàng toàn diện, giúp tối ưu hóa công tác chăm sóc khách hàng và hỗ trợ các bộ phận Marketing, Sales, và CSKH trong doanh nghiệp. Tài liệu hướng dẫn sử dụng Getfly CRM bao gồm các phần chính sau:

1. Getfly CRM: Cung cấp các tài liệu hướng dẫn chi tiết về các tính năng của hệ thống, kèm theo các kênh hỗ trợ như hotline, email và live chat.

2. Ứng dụng Getfly: Hướng dẫn tải và sử dụng ứng dụng Getfly trên di động, bao gồm quản lý tài khoản, chat nội bộ, công cụ chấm công, và các quy trình trong doanh nghiệp.

3. Phiên bản Web: Hướng dẫn cài đặt và sử dụng các tính năng cơ bản như quản lý khách hàng, bán hàng, marketing (email, SMS, chiến dịch tự động), quản lý công việc, KPI và báo cáo chi tiết về khách hàng, nhân viên, phòng ban, sản phẩm và chiến dịch.

4. Tính năng mở rộng: Bao gồm tích hợp tổng đài, quản lý kho, tài chính kế toán, nhân sự (HRM), và Social CRM (Facebook, Zalo). Các công cụ này giúp doanh nghiệp quản lý tốt hơn các hoạt động nội bộ và tương tác với khách hàng.

5. Đối tác kết nối: Hướng dẫn tích hợp với các đối tác như KiotViet, Google Drive, Shopee, tổng đài, email, SMS và các đối tác giao vận.

6. Tài liệu API và FAQ: Cung cấp tài liệu về API để tích hợp với hệ thống khác và giải đáp các câu hỏi thường gặp.

Tổng quát, Getfly CRM cung cấp một nền tảng toàn diện hỗ trợ doanh nghiệp trong việc quản lý và tối ưu hóa các hoạt động bán hàng, marketing, chăm sóc khách hàng, nhân sự, tài chính, và kho bãi.

# VAI TRÒ & NHIỆM VỤ
- Bạn là Getfly Pro, trợ lý AI chuyên nghiệp của nền tảng Getfly CRM.
- Nhiệm vụ: Hỗ trợ người dùng giải quyết các vấn đề liên quan đến Getfly CRM.
- Cam kết: Cung cấp thông tin chính xác, hữu ích và thân thiện.

# PIPELINE
Suy nghĩ thật kĩ và thực hiện từng bước theo flow Mermaid dưới đây:
    A[Bắt đầu] --> C[Dựa vào bối cảnh trò chuyện, nhận định xem có đủ thông tin để trả lời đầu vào của người dùng hay không?]

    C -->|Không đủ thông tin| D[Yêu cầu người dùng làm rõ thêm]
    
    C -->|Đủ thông tin| E[Phân tích bối cảnh trò chuyện bao gồm các nội dung dưới đây:
    - Đầu vào của người dùng
    - Lịch sử trò chuyện
    - Bản tóm tắt lịch sử trò chuyện]
    
    D --> I[Gửi câu trả lời]
    
    E --> F[Chọn lọc ra những nội dung liên quan nhất đến đầu vào của người dùng]
    
    F --> G[Tạo câu trả lời:
    - Logic
    - Tự nhiên
    - Sâu sắc
    - Không sử dụng câu hỏi mở
    - Dùng ít nhất 4 câu]
    
    G --> I[Gửi câu trả lời]
    
    I --> J[Kết thúc]


# BỐI CẢNH TRÒ CHUYỆN
1. Lịch sử trò chuyện:
```
{pqa}
```

2. Tóm tắt lịch sử trò chuyện:
```
{summary_history}
```

3. Đầu vào của người dùng
```
{original_query}
```
"""


class AnswerGenerator:
    def __init__(
        self,
        chat_generator: ChatGenerator,
        settings: dict = None
    ) -> None:
        self.chat_generator = chat_generator
        self.settings = settings if settings else GETFLY_BOT_SETTINGS
        self.timezone = pytz.timezone(self.settings["timezone"])


    def run(self, messages: List[ChatMessage], relevant_documents: List[dict], summary_history: str, original_query: str) -> str:
        if len(relevant_documents) == 0:
            return self.runNoContext(messages=messages, 
                                    summary_history=summary_history,
                                    original_query=original_query,
                                    )
        return self.runWithContext(messages=messages, 
                                relevant_documents=relevant_documents, 
                                summary_history=summary_history,
                                original_query=original_query,
                                )
                                


    @observe(name="AnswerGeneratorWithContext")
    async def runWithContext(self, messages: List[ChatMessage], relevant_documents: List[RelevantDocument], summary_history: str, original_query: str) -> str:
        relevant_documents = [RelevantDocument(
            id=doc['id'],
            text=doc['text'],
            child_link=doc['child_link'],
            page_content=doc['page_content'],
            enriched_content=doc['enriched_content'],
            url=doc['url'],
            score=doc.get('score'),
            cross_score=doc.get('cross_score'),
            context_string=doc.get('context_string'),
            context=doc.get('context')
        ) for doc in relevant_documents]
        
        
        current_time = datetime.now(self.timezone).strftime("%A, %Y-%m-%d %H:%M:%S")
        taken_messages = messages[-5:-1]
        pqa: str = "\n".join(map(lambda message: f"{message.role}: {message.content}", taken_messages))
        def format_document(index, doc):
            doc_start = f"\t<Document {index}>\n"
            url_line = f"\t\Chunk_ID: {doc.id}\n"
            content_line = f"\t\t{doc.page_content}\n"
            doc_end = f"\t</Document {index}>"
            return doc_start + url_line + content_line + doc_end

        context: str = "\n".join(
            format_document(i, doc) 
            for i, doc in enumerate(relevant_documents, 1)
        )



        # Thêm cấu hình Retry
        retry_settings = {
            "max_retries": 5,  # Số lần thử lại tối đa
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
                        original_query=original_query,
                        ), 
                    temperature=0.2,
                    response_model=ChatResponseWithContext
                    )
                

                answer = result.answer
                references = result.references
                child_links = set()


                db = SessionLocal()
                enriched_references = []
                if references:
                    sorted_references = sorted(references, key=lambda ref: ref.score, reverse=True)

                    for ref in sorted_references:
                        chunk_id = ref.chunk_id
                        embedding = db.query(Embedding).filter(Embedding.chunk_id == chunk_id).first()
                        if embedding:
                            relevant_doc = next((doc for doc in relevant_documents if str(doc.id) == str(chunk_id)), None)

                            enriched_ref = {
                                "child_link": embedding.child_link if embedding.child_link else chunk_id,
                                "score": ref.score,
                                "page_content": embedding.page_content,
                                "context": relevant_doc.context
                            }
                            enriched_references.append(enriched_ref)
                            if embedding.child_link:
                                child_links.add(embedding.child_link)

                    references_str = "\n".join(f"- {link}" for link in child_links)
                    final_answer = f"{answer}\n\nXem thêm:\n{references_str}"
                else:
                    final_answer = answer
                

                return {
                    "context_analysis": result.context_analysis,
                    "is_query_answerable": result.is_query_answerable,
                    "answer": answer,
                    "references": enriched_references,
                    "child_links": child_links
                }
        
            except Exception as e:
                logger.error(f"Error in runWithContext: {str(e)}")
                if attempt < retry_settings["max_retries"] - 1:
                    delay = min(retry_settings["initial_delay"] * (retry_settings["multiplier"] ** attempt), retry_settings["max_delay"])
                    await asyncio.sleep(delay)
                else:
                    raise e

    @observe(name="FormatAnswer") 
    def format_answer(self, answer: str) -> str:
        answer = answer.replace("```", "")
        # Xử lý xuống hàng
        answer = re.sub(r'([.!?])\s{2}', r'\1\n\n', answer)
        # Thay thế ký tự xuống dòng \n bằng một dòng mới
        answer = answer.replace('\\n', '\n')
        items = [item.strip() for item in answer.split('\n\n') if item.strip()]
        return {
            "answer": answer.replace('\\', ''),
            "items": items
        }
            



    @observe(name="AnswerGeneratorNoContext")
    async def runNoContext(self, messages: List[ChatMessage], summary_history: str, original_query: str) -> str:
        current_time = datetime.now(self.timezone).strftime("%A, %Y-%m-%d %H:%M:%S")
        taken_messages = messages[-5:-1]
        pqa: str = "\n".join(map(lambda message: f"{message.role}: {message.content}", taken_messages))

        # Thêm cấu hình Retry
        retry_settings = {
            "max_retries": 5,  # Số lần thử lại tối đa
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
                        current_time=current_time), 
                    temperature=0.2,
                    response_model=ChatResponseWithNoContext
                    )
                return {
                    "context_analysis": text.context_analysis,
                    "is_query_answerable": text.is_query_answerable,
                    "answer": text.answer,
                }
            except Exception as e:
                if attempt < retry_settings["max_retries"] - 1:
                    # Tính toán thời gian chờ với max_delay
                    delay = min(retry_settings["initial_delay"] * (retry_settings["multiplier"] ** attempt), retry_settings["max_delay"])
                    await asyncio.sleep(delay)
                else:
                    raise e



    # 1. Nhận diện xem người dùng có yêu cầu kết nối đến bộ phậm chăm sóc khách hàng hay không
    # 2. Phân tích ngữ cảnh được cung cấp: Bao gồm đầu vào của người dùng, lịch sử trò chuyện, bản tóm tắt lịch sử trò chuyện
    # 3. Với ngữ cảnh dược cung cấp, nhận định xem đầu vào của người dùng có rõ ràng không. Nếu không rõ ràng thì thay vì trả lời hãy đề nghị người dùng làm rõ thêm đầu vào
    # 4. Chọn nội dung liên quan nhất đến đầu vào của người dùng từ ngữ cảnh được cung cấp và sử dụng nó để tạo câu trả lời ngắn gọn nhưng logic, tự nhiên, sâu sắc (trong câu trả lời không trích dẫn Chunk ID)
    # 5. Trích dẫn Chunk ID của các Document mà bạn đã sử dụng để trả lời đầu vào của người dùng
    # 6. Không sử dụng câu hỏi mở trong câu trả lời