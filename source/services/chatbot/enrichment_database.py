import sys
import os

# Thêm path của thư mục source vào PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
source_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.append(source_dir)
from langfuse.decorators import observe
from source.services.chatbot.generator import Generator, VertexAIGenerator
from source.services.chatbot.database import get_db, Embedding
from google.oauth2.service_account import Credentials
import asyncio
from tenacity import retry, wait_exponential

credentials = Credentials.from_service_account_file(
    "/home/datpt/project/communi_ai_6061cfee10dd.json",
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)

system_prompt = """\
# HƯỚNG DẪN
Nhiệm vụ của bạn là làm phong phú nội dung được viết dưới dạng markdown, để tăng cường hiệu quả cho kỹ thuật xếp hạng lại (reranking). Dưới đây là các bước cụ thể bạn cần thực hiện:

1. **Tạo tài liệu tự giải thích**: Đảm bảo rằng đầu ra có thể được đọc như một tài liệu độc lập và tự giải thích bằng tiếng Việt, không cần tham chiếu bất kỳ tài liệu "nguồn" nào hoặc các tham chiếu bên ngoài.
 
2. **Tổ chức nội dung có logic**: Sử dụng các tiêu đề rõ ràng để tổ chức nội dung một cách hợp lý và dễ dàng theo dõi.

3. **Tránh sử dụng định dạng markdown**: Tập trung vào văn bản mô tả và thông tin để tăng cường khả năng tìm kiếm toàn diện hơn là định dạng markdown.

4. **Tuân thủ phạm vi của nội dung gốc**: Chỉ làm phong phú nội dung dựa trên những gì đã được cung cấp - không thêm thông tin không được nêu rõ hoặc ngụ ý trực tiếp bởi nguồn.

5. **Đơn giản hóa nội dung**: Khi không có đủ nội dung để mở rộng một khía cạnh cụ thể, để phần đó trống thay vì tạo ra bổ sung giả định.

6. **Trả lại nội dung duy nhất**: Chỉ trả lại nội dung đã làm phong phú như yêu cầu, không có bất kỳ giải thích thêm nào.

Dưới đây là phần nội dung markdown mẫu, bạn sẽ cần làm phong phú nó theo các hướng dẫn trên:

```markdown
{content}
```

Sau khi nhận được nội dung thực tế, bạn sẽ làm phong phú nó thêm mà không làm thay đổi ý nghĩa gốc của nội dung ban đầu.


# ĐỊNH DẠNG ĐẦU RA
Câu trả lời của bạn luôn bao gồm hai phần (Hai khối phần tử):
<ANALYZING>
Đây là nơi bạn viết phân tích của mình (Phân tích của bạn nên bao gồm: Lý luận, Vì sao lại có những nội dung như vậy, Các mối phụ thuộc, Ngôn ngữ sử dụng)
</ANALYZING>
<REWRITTEN_QUERY>
Đây là nơi bạn chỉ xuất ra nội dung độc lập thực tế. (Giữ nguyên ngôn ngữ như đầu vào của người dùng). Chỉ xuất ra nội dung viết lại độc lập. Không thêm bất kỳ bình luận nào.
</REWRITTEN_QUERY>
"""




class EnrichmentDatabase:
    def __init__(
        self,
        generator: Generator,
    ) -> None:
        self.generator = generator

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    @observe(name="EnrichmentDatabase") 
    async def run(self, chunk_id: int, page_content: str) -> str:
        text = await self.generator.run(
            prompt=system_prompt.format(content=page_content),
            temperature=0.2
        )


        text = text.split("<REWRITTEN_QUERY>")[1].split("</REWRITTEN_QUERY>")[0].strip()
        
        return text.strip('```').strip() if text.startswith('```') else text.strip() 

        

    


if __name__ == "__main__":
    # Lấy database session
    db = next(get_db())
    
    # Khởi tạo và chạy enrichment
    generator_flash = VertexAIGenerator(
        model="gemini-1.5-pro-002", 
        project_id="communi-ai", 
        location="asia-southeast1", 
        credentials=credentials
    )
    enrichment = EnrichmentDatabase(generator=generator_flash)

    # Lấy tất cả records cần xử lý
    embeddings = db.query(Embedding).filter(
        Embedding.customer_id == 'VPBank').all()

    async def process_all():
        for embedding in embeddings:
            try:
                print(f"Processing chunk {embedding.chunk_id}")
                enriched_text = await enrichment.run(
                    chunk_id=embedding.chunk_id,
                    page_content=embedding.page_content
                )
                embedding.enriched_content = enriched_text
                db.commit()
                print(f"Successfully processed chunk {embedding.chunk_id}")
                await asyncio.sleep(3)  # Delay 3s
            except Exception as e:
                print(f"Error processing chunk {embedding.chunk_id}: {str(e)}")
                continue

    # Chạy tất cả trong 1 event loop
    asyncio.run(process_all())