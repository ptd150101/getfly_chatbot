import streamlit as st
import requests
import json
import re
from markdown2 import markdown
from bs4 import BeautifulSoup

def markdown_to_text(markdown_content):
    # Convert markdown to HTML with extra features like lists
    html = markdown(markdown_content, extras=["fenced-code-blocks", "cuddled-lists", "tables", "numbering"])
    
    # Parse the HTML to preserve list formatting
    soup = BeautifulSoup(html, "html.parser")
    
    # Process ordered lists and unordered lists
    def process_list_items(soup):
        for ol in soup.find_all("ol"):
            start = int(ol.get("start", 1))  # Get start attribute if exists, default to 1
            for i, li in enumerate(ol.find_all("li"), start):
                li.insert_before(f"{i}. ")  # Add numbering before each list item
            ol.unwrap()  # Remove the ol tag, but keep its contents

        for ul in soup.find_all("ul"):
            for li in ul.find_all("li"):
                li.insert_before("- ")  # Add a dash before each list item
            ul.unwrap()  # Remove the ul tag, but keep its contents

    process_list_items(soup)
    
    text = soup.get_text()
    return text




# API Configuration
API_URL = "http://localhost:2000/streamlit"
# Page Configuration 
st.set_page_config(
    page_title="Getfly Assistant",
    page_icon="🤖",
    layout="wide"
)

# Initialize session state for chat history if not exists
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Xin chào! Tôi là trợ lý Getfly. Tôi có thể giúp gì cho bạn?"}
    ]

if "max_references" not in st.session_state:
    st.session_state.max_references = 3


# Display chat title
st.title("💬 Getfly Assistant")

# Display chat history with proper styling for each message
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Modified message display code
if prompt := st.chat_input("Nhập câu hỏi của bạn..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.write(prompt)

    try:
        response = requests.post(
            f"{API_URL}",
            json={
                "content": prompt,
                "histories": st.session_state.messages,
            },
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            responses = response.json()
            
            references = responses.get("data", {}).get("references", [])
            print(f"Số lượng references: {len(references)}")

            max_ref = min(st.session_state.max_references, len(references))
            selected_references = references[:max_ref]

            print(f"Số lượng selected references: {len(selected_references)}")
            
            original_answer = responses.get("data", {}).get("original_answer", "")
            summary_history = responses.get("data", {}).get("summary_history", "")
            

            text_response = False


            for resp in responses.get("data", {}).get("content", []):
                if resp.get("type") == "text" and not text_response:
                    with st.chat_message("assistant"):
                        st.write(original_answer)
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": original_answer
                    })    

                    # Hiển thị references với markdown links
                    if selected_references:
                        embedded_links = []
                        for ref in selected_references:
                            content_lines = ref.get('page_content', '').split('\n')
                            
                            # Lấy dòng đầu tiên
                            first_line = content_lines[0].strip() if content_lines else ''
                            
                            # Tìm header cuối cùng (header có nhiều # nhất)
                            last_header = ref.get('last_header', '')
                            child_link = ref.get('child_link', '')
                            
                            if first_line:
                                if last_header:
                                    last_header = re.sub(r'\s*<a href="#undefined" id="undefined"></a>', '', last_header)
                                    # Xử lý first_line để lấy 2 cấp cuối cùng
                                    path_parts = first_line.split('>')
                                    if len(path_parts) >= 2:
                                        first_line = f"{path_parts[-2].strip()} › {path_parts[-1].strip()}"
                                    elif len(path_parts) == 1:
                                        first_line = path_parts[0].strip()
                                    
                                    first_line = first_line.replace('**', '').replace('>', '›')
                                    last_header = last_header.replace('**', '').replace('>', '›')
                                    if last_header.endswith(f"{first_line}"):
                                        title = markdown_to_text(last_header)
                                    else:
                                        title = f"{first_line} › {markdown_to_text(last_header)}"
                                        
                                    print(f"[{title}]({child_link})")
                                    embedded_links.append(f"[{title}]({child_link})")
                                else:
                                    path_parts = first_line.split('>')
                                    if len(path_parts) >= 2:
                                        first_line = f"{path_parts[-2].strip()} › {path_parts[-1].strip()}"
                                    elif len(path_parts) == 1:
                                        first_line = path_parts[0].strip()
                                    
                                    first_line = first_line.replace('**', '').replace('>', '›')
                                    title = f"{first_line}"
                                        
                                    print(f"[{title}]({child_link})")
                                    embedded_links.append(f"[{title}]({child_link})")
                                                        
                        print("Embedded links: ", embedded_links)
                        if embedded_links:
                            references_str = "\n".join(f"- {link}" for link in embedded_links)
                            with st.chat_message("assistant"):
                                st.markdown(f"Xem thêm:\n{references_str}")
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": f"Xem thêm:\n{references_str}"
                            })
                    text_response = True



                elif resp.get("type") == "images":
                    with st.chat_message("assistant"):
                        cols = st.columns(5)  # Hiển thị 3 ảnh trên một hàng
                        for idx, img_url in enumerate(resp["content"]):
                            with cols[idx % 5]:  # Luân phiên giữa các cột
                                st.image(
                                    img_url,
                                    width=200,  # Cố định chiều rộng 200px
                                    use_column_width="auto",  # Hoặc dùng cái này để tự động điều chỉnh theo cột
                                )
                
                elif resp.get("type") == "videos":
                    with st.chat_message("assistant"):
                        cols = st.columns(5)  # Hiển thị 2 video trên một hàng
                        for idx, video_url in enumerate(resp["content"]):
                            with cols[idx % 5]:
                                st.video(
                                    video_url,
                                    format="video/mp4", 
                                    start_time=0
                                )

    except Exception as e:
        st.error(f"Error connecting to API: {str(e)}")
# Add instructions in sidebar
with st.sidebar:
    st.title("⚙️ Cài đặt")
    # Thêm slider để điều chỉnh số lượng references
    st.session_state.max_references = st.slider(
        "Số lượng tài liệu tham khảo tối đa",
        min_value=0,
        max_value=10,
        value=st.session_state.max_references,
        help="Điều chỉnh số lượng tài liệu tham khảo hiển thị trong mỗi câu trả lời"
    )



    st.title("Hướng dẫn sử dụng")
    st.markdown("""
    1. Nhập câu hỏi về Getfly vào ô chat
    2. Nhấn Enter để gửi câu hỏi
    3. Đợi phản hồi từ trợ lý
    
    **Lưu ý:** Trợ lý có thể trả lời các câu hỏi về:
    - Sử dụng Getfly CRM
    - Tính năng sản phẩm
    - Hướng dẫn cài đặt
    - API tích hợp
    """)
