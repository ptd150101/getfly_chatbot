import streamlit as st
import requests
import os
import json

# API Configuration
API_URL = "http://localhost:2222"

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
            f"{API_URL}/chat",
            json={
                "content": prompt,
                "histories": st.session_state.messages,
                "summary": "",
            },
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            responses = response.json()
            for resp in responses.get("data", {}).get("content", []):
                if resp.get("type") == "text":
                    with st.chat_message("assistant"):
                        st.write(resp["content"])
                    # Lưu text vào session state
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": resp["content"]
                    })
                
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