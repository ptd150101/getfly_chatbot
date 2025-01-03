from generator import Generator
from logging import getLogger
import asyncio
from dotenv import load_dotenv
import os
from pydantic import BaseModel, Field, field_validator

class ContextualRetrieval(BaseModel):
    analysis: str = Field(description="Phân tích ngữ cảnh được cung cấp: Bao gồm chunk và toàn bộ văn bản")
    contextual_retrieval: str = Field(description="Nội dung của chunk được viết lại để truy xuất các tài liệu liên quan từ cơ sở dữ liệu vector")

    @field_validator('analysis')  # Sửa tên trường ở đây
    @classmethod
    def validate_analysis(cls, v) -> str:
        if not v.strip():
            raise ValueError('Nội dung prompt không được để trống')
        return v


    @field_validator('contextual_retrieval')  # Sửa tên trường ở đây
    @classmethod
    def validate_contextual_retrieval(cls, v) -> str:
        if not v.strip():
            raise ValueError('Nội dung prompt không được để trống')
        return v



logger = getLogger(__name__)
load_dotenv()



system_prompt = """\
Bạn là một trợ lý AI chuyên về phần mềm CRM (phần mềm quản lý & chăm sóc khách hàng toàn diện), đặc biệt cho phần mềm Getfly CRM. Nhiệm vụ của bạn là cung cấp ngữ cảnh ngắn gọn, phù hợp cho một đoạn văn từ tài liệu hướng dẫn sử dụng của Getfly CRM.

Đây là tài liệu hướng dẫn sử dụng:
```
<document>
{document}
</document>
```

Đây là đoạn văn mà chúng tôi muốn đặt trong ngữ cảnh của toàn bộ tài liệu:
```
<chunk>
{chunk}
</chunk>
```

Suy nghĩ từng bước và thực hiện theo các hướng dẫn sau:
1. Xác định tính năng hoặc chức năng chính được thảo luận (ví dụ: quản lý khách hàng, chăm sóc khách hàng, theo dõi giao dịch, báo cáo thống kê).

2. Đề cập đến các tình huống hoặc kịch bản sử dụng liên quan (ví dụ: quy trình tạo lead, quy trình chăm sóc khách hàng, báo cáo hiệu suất hàng tháng).

3. Nếu có thể, lưu ý cách thông tin này liên quan đến hiệu quả sử dụng phần mềm, cải thiện hiệu suất công việc hoặc tối ưu hóa quy trình chăm sóc khách hàng.

4. Bao gồm bất kỳ tính năng hoặc hướng dẫn quan trọng nào giúp người dùng sử dụng phần mềm hiệu quả hơn.

5. Bao gồm bất kỳ số liệu hoặc phần trăm quan trọng nào cung cấp ngữ cảnh đáng chú ý.

6. Không sử dụng các cụm từ như "Đoạn văn này đề cập đến" hoặc "Phần này cung cấp". Thay vào đó, hãy trực tiếp nêu ngữ cảnh.

7. Hãy đưa ra ngữ cảnh ngắn gọn để đặt đoạn văn này trong toàn bộ tài liệu nhằm cải thiện khả năng tìm kiếm đoạn văn trong cơ sở dữ liệu vector.
"""




class EnrichmentDatabase:
    def __init__(
        self,
        generator: Generator,
        max_retries: int = 20,
        retry_delay: float = 2.0
    ) -> None:
        self.generator = generator
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def run(self, document, page_content: str) -> str:
        for attempt in range(self.max_retries):
            try:
                text = await self.generator.run(
                    prompt=system_prompt.format(
                        document=document,
                        chunk=page_content,
                        ),
                    temperature=0.2,
                    response_model=ContextualRetrieval,
                )

                result = {
                    "analysis": text.analysis,
                    "contextual_retrieval": text.contextual_retrieval,
                }
                return f"{result.get('contextual_retrieval', '')}\n\n{page_content}"
            except Exception as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                else:
                    return os.getenv("OVERLOAD_MESSAGE")