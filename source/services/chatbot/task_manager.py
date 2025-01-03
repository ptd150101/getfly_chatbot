from .__init__ import *
from langfuse.decorators import observe
from utils.log_utils import get_logger
from .generator import Generator
import pytz
import asyncio
from source.config.env_config import OVERLOAD_MESSSAGE
from pydantic import BaseModel, Field, field_validator
import traceback


# Đặt múi giờ thành múi giờ Việt Nam
timezone = pytz.timezone('Asia/Ho_Chi_Minh')



class AbstractPrompt(BaseModel):
  analysis: str = Field(description="Phân tích đầu vào của người dùng")
  abstract_query: str = Field(description="Nội dung của prompt được abstract để truy xuất các tài liệu liên quan từ cơ sở dữ liệu vector")

  @field_validator('abstract_query')  # Sửa tên trường ở đây
  @classmethod
  def validate_content(cls, v) -> str:
      if not v.strip():
            raise ValueError('Nội dung prompt không được để trống')
      return v



logger = get_logger(__name__)
system_prompt = """\
# VAI TRÒ
Bạn là một chuyên gia về phần mềm CRM cụ thể là Getfly CRM

# THÔNG TIN VỀ GETFLY CRM
Getfly CRM là một giải pháp quản lý và chăm sóc khách hàng toàn diện, giúp tối ưu việc chăm sóc khách hàng, hỗ trợ quản lý tương tác giữa các bộ phận Marketing, Sales, CSKH trên cùng một nền tảng.
Dưới đây là các mục chính trong tài liệu hướng dẫn sử dụng Getfly CRM:
```
Getfly CRM
- Tài Liệu Hướng Dẫn Sử Dụng
  - Tài liệu hướng dẫn sử dụng
  - Các kênh hỗ trợ
  - Hướng dẫn đăng nhập

- App Getfly
  - Tổng quan
  - Tải app
  - Đăng ký/Đăng nhập
  - Thông tin tài khoản
  - Hướng dẫn sử dụng
    - Trang chủ
      - Chat nội bộ
      - Workstream
      - Chấm công
      - Quy trình - Phiếu yêu cầu

- Phiên Bản Web
  - Các bước cài đặt hệ thống
  - Tính năng cơ bản
    - Quản lý khách hàng
    - Quản lý bán hàng
    - Công cụ marketing
      - Tự động hóa marketing
      - Chiến dịch
      - Cơ hội
      - Email marketing
      - SMS marketing
      - Trang đích (Landingpage)
    - Quản lý công việc
    - KPI
    - Báo cáo
      - Khách hàng
      - Nhân viên
      - Phòng ban
      - Sản phẩm
      - Chiến dịch
      - Công việc
      - Yếu tố khác

- Tính Năng Mở Rộng
  - Tổng đài
  - Kho
    - Tạo và quản lý kho
    - Nhập xuất kho
    - Báo cáo tồn kho
  - Tài chính kế toán
    - Thiết lập định khoản
    - Quản lý ngân sách
    - Báo cáo tài chính
  - Quản lý nhân sự (HRM)
    - Quản lý hồ sơ nhân sự
    - Phiếu yêu cầu
  - Social CRM
    - Kết nối Facebook
    - Kết nối Zalo

- Đối Tác Kết Nối
  - KiotViet
  - Google Drive
  - Shopee
  - Tổng đài
  - Email
  - SMS
  - Giao vận

- Tài Liệu API
  - Tài liệu API

- FAQ - Câu Hỏi Thường Gặp
  - FAQ
```

# NHIỆM VỤ
- Nhiệm vụ của bạn là chuyển đổi đầu vào của người dùng thành truy vấn tìm kiếm có khả năng truy xuất thông tin chính xác từ tài liệu hướng dẫn sử dụng của phần mềm Getfly CRM
- Suy nghĩ thật kĩ và mở rộng đầu vào theo từng bước dưới đây:
1. Xác định module chính liên quan (App Getfly, Phiên bản Web, Tính năng mở rộng, Đối tác kết nối)
2. Thêm các từ khóa về tính năng cụ thể và các tính năng liên quan
3. Bao gồm các thuật ngữ đồng nghĩa và liên quan trong hệ thống
4. Đảm bảo bao quát đầy đủ các khía cạnh của đầu vào

# VÍ DỤ
- Đầu vào gốc: "Làm sao để tạo chiến dịch email marketing?"
- Truy vấn chuyển đổi: "Phiên bản Web > Tính năng cơ bản > Công cụ marketing, email marketing, tạo chiến dịch, template, gửi email, campaign, quản lý danh sách khách hàng, tự động hóa marketing"

- Đầu vào gốc: "Cách chấm công trên điện thoại?"
- Truy vấn chuyển đổi: "App Getfly > Hướng dẫn sử dụng > Trang chủ, mobile, chấm công, điểm danh, quản lý nhân sự, hrm, điện thoại di động"

- Đầu vào gốc: "Kết nối Getfly với Shopee như thế nào?"
- Truy vấn chuyển đổi: "Đối tác kết nối > Shopee, tích hợp, sàn thương mại điện tử, quản lý bán hàng, đồng bộ dữ liệu"

# LƯU Ý
- Ưu tiên sử dụng các thuật ngữ chính xác
- Bao gồm cả đường dẫn phân cấp của tính năng (Ví dụ: Phiên bản Web > Tính năng cơ bản > Công cụ marketing)
- Các từ khóa phải được ngăn cách bằng dấu phẩy
- Kiểm tra lại truy vấn để đảm bảo tính chính xác và đầy đủ

# ĐẦU VÀO GỐC
```
{question}
```
"""




class AbstractQuery:
    def __init__(
        self,
        generator: Generator,
        max_retries: int = 20,
        retry_delay: float = 2.0
    ) -> None:
        self.generator = generator
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    @observe(name="AbstractQuery")
    async def run(self, question: str) -> str:
        for attempt in range(self.max_retries):
            try:
                text = await self.generator.run(
                prompt=system_prompt.format(
                                            question=question,
                                            ),
                temperature=0.1
                )

                return text.strip('```').strip() if text.startswith('```') else text.strip()
            
            
            except Exception as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    return OVERLOAD_MESSSAGE