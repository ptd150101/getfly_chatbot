import re
def get_header_level(line):
    match = re.match(r'^(#+)\s', line)
    return len(match.group(1)) if match else 0


def generate_chunks(content):
    chunks = []
    current_chunk = []
    header_stack = []
    content_after_header = False
    chunk_index = 1  # Thêm biến đếm index

    for line in content.split('\n'):
        level = get_header_level(line)

        if level > 0:
            if content_after_header and current_chunk:
                chunks.append({
                    'content': '\n'.join(current_chunk),
                    'index': chunk_index
                })
                chunk_index += 1
                current_chunk = []
            
            while header_stack and header_stack[-1][0] >= level:
                header_stack.pop()

            header_stack.append((level, line.strip()))
            
            current_chunk = [header for _, header in sorted(header_stack)]
            content_after_header = False
        else:
            if line.strip():
                content_after_header = True
            current_chunk.append(line.rstrip())

    if current_chunk:
        chunks.append({
            'content': '\n'.join(current_chunk),
            'index': chunk_index
        })

    return chunks


content = """# Tạo và quản lý Kho

## 1. **Tạo mới, chỉnh sửa và xóa kho**

### 1.1. Tạo mới kho

Để tạo mới kho bạn truy cập module **Kho** -> chọn **Kho** -> **Thêm mới**

<figure><img src="https://3678814682-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2FiGaDgB2Rdx0J8VdIy5oL%2Fuploads%2FrYrssscBAZaKLDoEeHk5%2FScreenshot_6.png?alt=media&#x26;token=c83bdc0d-f2d6-4e13-905b-ea060abe3767" alt=""><figcaption></figcaption></figure>

Màn hình thêm mới Kho hiển thị các thông tin sau:

<figure><img src="https://3678814682-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2FiGaDgB2Rdx0J8VdIy5oL%2Fuploads%2F2oMYBXmMLiuWB1bHxEhw%2FScreenshot_7.png?alt=media&#x26;token=23c027a2-de5d-42f6-974a-cb1af524e12e" alt=""><figcaption></figcaption></figure>

(1) Tên kho: tên của khcần tạo

(2) Mã Kho: tạo mã kho mục tiêu để sau này khi upload đơn hàng mua hoặc đơn hàng bán có thông tin mã kho cần xuất hàng hoặc cần nhập hàng

(3) Địa chỉ kho: để nhận biết địa chỉ kho

(4) Số điện thoại của kho nếu có

(5) Thủ kho: chỉ định ai sẽ là thủ kho của kho này. Thủ kho sẽ là người kết thúc các quy trình nhập kho, xuất kho, kiểm kho

(6) Người liên quan: chỉ định ai được tham gia trong kho, người tham gia xem và kiểm tra được số lượng sản phẩm tồn của kho liên quan

Sau khi hoàn tất click **Thêm mới** để tạo Kho

### 1.2. Chỉnh sửa kho

Bạn truy cập Kho -> chọn Kho, màn hình hiển thị các danh sách Kho trên hệ thống, chọn kho cần chỉnh sửa

<figure><img src="https://3678814682-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2FiGaDgB2Rdx0J8VdIy5oL%2Fuploads%2FzOloDIqhJkO4klENOAHP%2FScreenshot_8.png?alt=media&#x26;token=31ea5bab-5091-45a3-924d-c1e64c557e3e" alt=""><figcaption></figcaption></figure>

### 1.3. Xóa kho

Bạn truy cập Kho -> chọn Kho, màn hình hiển thị các danh sách Kho trên hệ thống, chọn kho cần xóa

<figure><img src="https://3678814682-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2FiGaDgB2Rdx0J8VdIy5oL%2Fuploads%2F2JagUjTZXzEGZUxVORiF%2FScreenshot_9.png?alt=media&#x26;token=f4d158a6-4c20-4411-9e56-1a36889273bb" alt=""><figcaption></figcaption></figure>

**Lưu ý:**

* Trước khi xóa kho cần thao tác chuyển hết hàng tồn của kho sang một kho khác
* Kho sau khi xoá sẽ nằm ở mục **Đã xoá**, bạn có thể khôi phục kho nếu cần

<figure><img src="https://wiki.getfly.vn/public/img/images/image(61).png" alt=""><figcaption></figcaption></figure>

## 2. **Thiết lập quy trình kho**

### 2.1. Bặt/tắt quy trình duyệt kho

Trước khi bạn có thể thiết lập quy trình duyệt cho kho trong Getfly CRM, bạn cần bật tính năng quy trình duyệt chung cho hệ thống CRM. Bạn truy cập **Cài đặt** -> **Cấu hình hệ thống** -> **Cấu hình CRM** -> **Quy trình duyệt** -> lựa chọn **Sử dụng quy trình duyệt Kho**&#x20;

<figure><img src="https://3678814682-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2FiGaDgB2Rdx0J8VdIy5oL%2Fuploads%2FKwKi0IG7XgmGQdUpdZpg%2FScreenshot_10.png?alt=media&#x26;token=761e9f0a-c5f7-408e-96d8-32fed27c3abc" alt=""><figcaption></figcaption></figure>

* Bật: có sử dụng quy trình duyệt kho (có thể tạo phiếu xuất kho khi sản phẩm hết hàng)&#x20;
* Tắt: không sử dụng quy trình duyệt kho (không thể tạo phiếu xuất kho khi sản phẩm hết hàng)

### 2.2. Thiết lập quy trình xuất kho, nhập kho và kiểm kho

Sau khi đã bật quy trình duyệt kho bạn có thể cài đặt chi tiết quy trình xuất, nhập và kiểm kho theo từng kho khác nhau. Bạn truy cập vào **Kho** -> chọn chỉnh sửa Kho -> **Thiết lập quy trình**

<figure><img src="https://3678814682-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2FiGaDgB2Rdx0J8VdIy5oL%2Fuploads%2FCHOpQC8OAVhoYQPcL6xM%2FScreenshot_1.png?alt=media&#x26;token=0eef7ec8-54a0-4037-91e1-d693898cbea0" alt=""><figcaption></figcaption></figure>

(1) **Ai được quyền yêu cầu nhập kho:** lựa chọn tài khoản có quyền tạo phiếu nhập kho

(2) **Người được chỉ định kết thúc quy trình nhập kho:** khi bạn chọn thủ kho thì hệ thống mặc định người thủ kho là người kết thúc quy trình tuy nhiên bạn có thể chỉ định được người khác hoặc thêm người kết thúc quy trình nhập kho (trường hợp khi thủ kho vắng mặt hoặc bận thì phụ kho vẫn duyệt để kết thúc quy trình)

(3) Trường hợp lựa chọn **thêm người xác nhận** thì cần xác nhận theo quy trình người được chỉ định thêm xác nhận sẽ duyệt trước sau đó sẽ tới người được chỉ định kết thúc quy trình &#x20;

Tương tự, bạn có thể setup quy trình **xuất kho** và **kiểm kho**

Sau khi hoàn tất quy trình duyệt bạn chọn **Thêm mới** để lưu lại quy trình

## 3. **Quản lý kho**

Bạn truy cập vào module **Kho** -> chọn **Kho,** màn hình hiển thị danh sách toàn bộ kho trên hệ thống

<figure><img src="https://3678814682-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2FiGaDgB2Rdx0J8VdIy5oL%2Fuploads%2FrhIylUkbOtpdmKxdEX3U%2FScreenshot_13.png?alt=media&#x26;token=71884c55-5273-4bf1-8a8f-329b57e11ee7" alt=""><figcaption></figcaption></figure>

(1) **Tìm kiếm**: theo mã kho, tên kho

(2) **Trạng thái kho**: đang sử dụng/đã xóa

(3) **Danh sách toàn bộ kho trên hệ thống**: tên kho, thông tin thủ kho, địa chỉ kho

## 4. Video hướng dẫn

{% embed url="https://youtu.be/W4gXES5Psf0?si=3GPvTxKc0wriptfY" %}
"""

chunks = generate_chunks(content)

for chunk in chunks:
    print(f"Chunk {chunk['index']}:")
    print(chunk['content'])
    print("-" * 80)