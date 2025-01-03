from langfuse.decorators import observe
from utils.log_utils import get_logger
from .generator import Generator
import asyncio
from source.config.env_config import OVERLOAD_MESSAGE
from pydantic import BaseModel, Field, field_validator



class QuestionAnalysis(BaseModel):
   """Model for analyzing user questions based on complexity and Getfly relevance"""
   analysis: str = Field(description="Đây là nơi bạn viết các phân tích dùng để phục vụ cho câu trả lời")
   
   customer_service_request: bool = Field(
      default=None,
      description="Xác định xem người dùng có yêu cầu kết nối đến bộ phận chăm sóc khách hàng hay không?"
   )
   complexity_score: int = Field(
      description="Chấm điểm cho độ phức tạp của đầu vào từ 1-10, trong đó 1 là rất đơn giản và 10 là rất phức tạp",
      ge=1,  # greater than or equal to 1
      le=10  # less than or equal to 10
   )
   is_getfly_relevant: bool = Field(
      description="Chỉ ra xem đầu vào của người dùng có liên quan đến Getfly hay không?"
   )
   
   @field_validator('analysis')  # Sửa tên trường ở đây
   @classmethod
   def validate_analysis(cls, v):
      if not v.strip():
            raise ValueError('Phân tích không được để trống')
      return v

   @field_validator('customer_service_request')
   def check_customer_service_request(cls, v):
      if v is None:
         raise ValueError('Đánh giá tính rõ ràng của đầu vào không được để trống.')
      return v


   @field_validator('complexity_score')
   @classmethod
   def validate_complexity_score(cls, v) -> int:
      if not (1 <= v <= 10):
            raise ValueError('Complexity score must be between 1 and 5')
      return v
   
   @field_validator('is_getfly_relevant')
   @classmethod
   def validate_is_getfly_relevant(cls, v) -> bool:
      return v



logger = get_logger(__name__)
system_prompt = """\
# THÔNG TIN VỀ GETFLY
Getfly CRM là một giải pháp quản lý khách hàng toàn diện, giúp tối ưu hóa công tác chăm sóc khách hàng và hỗ trợ các bộ phận Marketing, Sales, và CSKH trong doanh nghiệp. Tài liệu hướng dẫn sử dụng Getfly CRM bao gồm các phần chính sau:

1. Getfly CRM: Cung cấp các tài liệu hướng dẫn chi tiết về các tính năng của hệ thống, kèm theo các kênh hỗ trợ như hotline, email và live chat.

2. Ứng dụng Getfly: Hướng dẫn tải và sử dụng ứng dụng Getfly trên di động, bao gồm quản lý tài khoản, chat nội bộ, công cụ chấm công, và các quy trình trong doanh nghiệp.

3. Phiên bản Web: Hướng dẫn cài đặt và sử dụng các tính năng cơ bản như quản lý khách hàng, bán hàng, marketing (email, SMS, chiến dịch tự động), quản lý công việc, KPI và báo cáo chi tiết về khách hàng, nhân viên, phòng ban, sản phẩm và chiến dịch.

4. Tính năng mở rộng: Bao gồm tích hợp tổng đài, quản lý kho, tài chính kế toán, nhân sự (HRM), và Social CRM (Facebook, Zalo). Các công cụ này giúp doanh nghiệp quản lý tốt hơn các hoạt động nội bộ và tương tác với khách hàng.

5. Đối tác kết nối: Hướng dẫn tích hợp với các đối tác như KiotViet, Google Drive, Shopee, tổng đài, email, SMS và các đối tác giao vận.

6. Tài liệu API và FAQ: Cung cấp tài liệu về API để tích hợp với hệ thống khác và giải đáp các câu hỏi thường gặp.

Tổng quát, Getfly CRM cung cấp một nền tảng toàn diện hỗ trợ doanh nghiệp trong việc quản lý và tối ưu hóa các hoạt động bán hàng, marketing, chăm sóc khách hàng, nhân sự, tài chính, và kho bãi.

# NHIỆM VỤ
Suy nghĩ thật kĩ và thực hiện phân tích đầu vào của người dùng theo từng bước dưới đây:
   1. Nhận diện xem người dùng có yêu cầu kết nối đến bộ phậm chăm sóc khách hàng hay không
   2. Độ phức tạp:
      - Đánh giá độ phức tạp của đầu vào của người dùng dựa vào độ dài, các mệnh đề và ý định có trong đầu vào (theo thang điểm từ 1 đến 10, trong đó 1 là rất đơn giản và 10 là rất phức tạp)
      - Nếu đầu vào của người dùng cần ít nhất hai prompt con để làm rõ thông tin thì độ phức tạp sẽ lớn hơn 3
   3. Mối liên quan với Getfly:
      - Xác định xem đầu vào của người dùng có liên quan đến Getfly hay không

# ĐẦU VÀO CỦA NGƯỜI DÙNG
```
{question}
```
"""


class RoutingQuestion:
   def __init__(
      self,
      generator: Generator,
      max_retries: int = 20,
      retry_delay: float = 2.0
   ) -> None:
      self.generator = generator
      self.max_retries = max_retries
      self.retry_delay = retry_delay

   @observe(name="RoutingQuestion")
   async def run(self, question: str) -> str:
      for attempt in range(self.max_retries):
         try:
            response = await self.generator.run(
                     prompt = system_prompt.format(
                        question=question,
                        ),
                     temperature = 0.2,
                     response_model=QuestionAnalysis,
            )
            result = {
               "analysis": response.analysis,
               "customer_service_request": response.customer_service_request,
               "complexity_score": response.complexity_score,
               "is_getfly_relevant": response.is_getfly_relevant
            }

            return result
         
         
         except Exception as e:
            if attempt < self.max_retries - 1:
               logger.warning(f"Lỗi khi gọi Enrichment (lần thử {attempt + 1}/{self.max_retries}): {str(e)}")
               await asyncio.sleep(self.retry_delay * (2 ** attempt))
            else:
               logger.error("Đã hết số lần thử lại. Không thể tăng cường.")
               return OVERLOAD_MESSAGE