from fastapi import APIRouter, Request, Form
from fastapi.responses import JSONResponse
from schemas.api_response_schema import ChatLogicInputData, ChatMessageRole, ChatMessage, make_response
from source.services.chatbot.chatbot_ai import AI_Chatbot_Service
from utils.log_utils import get_logger
from .database import SessionLocal, User, Thread, ChatHistory  # Import từ file database.py
import requests
import os
import json

logger = get_logger(__name__)
chat_router = APIRouter()

AI_CHATBOT_URL = os.getenv("AI_CHATBOT_URL", "http://127.0.0.1:6379")
top_k = 11

# Answer endpoint

ai_chatbot = AI_Chatbot_Service()

# Lưu trữ các thread đã tạo
threads = {}

# Biến toàn cục để lưu trữ lịch sử cuộc trò chuyện
conversation_history = {}
# Giả sử histories được lưu trong session state hoặc một biến toàn cục khác
histories = []

@chat_router.post("/chat")
async def create_answer_eng(user_data: ChatLogicInputData):
    try:
        if not user_data.content:
            logger.info("Empty Question")
            return make_response(-502, content="Empty content", summary_history="None")
        print(user_data)
        status_code, chatbot_answer, summary_history = await ai_chatbot.create_response(user_data)

        final_answer = make_response(status_code, content=chatbot_answer, summary_history=summary_history)
        logger.info(f"Final answer: {final_answer}")

    except Exception as e:
        chatbot_answer = f"Error in logic function: {e}"
        final_answer = make_response(-503, content=chatbot_answer, summary_history=summary_history)
    return final_answer

@chat_router.post("/summary")
async def summary_histories(user_data: ChatLogicInputData):
    summary_history = await ai_chatbot.create_summary(user_data)
    return summary_history

@chat_router.post("/threads")
def post_thread(request: dict):
    db = SessionLocal()
    global histories

    user_data = request.get('user')
    if user_data:
        # Kiểm tra xem user đã tồn tại chưa
        existing_user = db.query(User).filter(User.user_id == user_data['id']).first()
        if existing_user:
            logger.info(f"user_id {user_data['id']} đã tồn tại, không cần thêm mới.")
            user_id = existing_user.user_id  # Sử dụng user_id từ bảng users
        else:
            # Nếu chưa tồn tại thì thêm mới
            user = User(user_id=user_data['id'], display_name=user_data['display_name'])
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"user_id {user_data['id']} đã được thêm vào cơ sở dữ liệu.")
            user_id = user.user_id  # Sử dụng user_id từ bảng users

        # Tạo một bản ghi thread mới với đúng user_id từ bảng users
        new_thread = Thread(user_id=user_id)
        db.add(new_thread)
        db.commit()
        db.refresh(new_thread)
        
        logger.info(f"Thread được tạo với thread_id: {new_thread.thread_id}")
    
    print(request)
    
    # Thêm tin nhắn từ chatbot vào histories
    assistant_message = ChatMessage(role=ChatMessageRole.ASSISTANT, content="Hello, may I help you?")
    histories.append(assistant_message)
    
    return {
        "data": {
            "thread": {"id": new_thread.thread_id},
            "hello_message": {
                "content": assistant_message.content  # Lấy nội dung từ assistant_message
            }
        }
    }


@chat_router.post("/threads/{thread_id}/chat")
async def post_thread_chat(thread_id: int, request: dict):
    global conversation_history

    db = SessionLocal()

    # Lấy thông tin user_id từ thread
    thread = db.query(Thread).filter(Thread.thread_id == thread_id).first()
    if not thread:
        return {"error": "Thread not found"}

    user_id = thread.user_id  # Lấy user_id từ thread

    # **Kiểm tra và khởi tạo lại lịch sử chat cho thread mới**
    if thread_id not in conversation_history:
        conversation_history[thread_id] = []
        logger.info(f"Khởi tạo lịch sử chat cho thread_id {thread_id} với user_id {user_id}")

        # Thêm tin nhắn chào hỏi vào cuộc hội thoại
        welcome_message = ChatMessage(role=ChatMessageRole.ASSISTANT, content="Hello, may I help you?")
        conversation_history[thread_id].append(welcome_message)

    # Thêm tin nhắn từ người dùng vào cuộc hội thoại
    user_message = ChatMessage(role=ChatMessageRole.USER, content=request["content"])
    conversation_history[thread_id].append(user_message)

    # Tạo đối tượng ChatLogicInputData từ request và thread_id
    chat_logic_input = ChatLogicInputData(
        thread_id=str(thread_id),
        content=request["content"],
        histories=conversation_history[thread_id],
        user_id=str(user_id)
    )
    
    # Gọi hàm xử lý logic từ /chat
    final_answer = await create_answer_eng(chat_logic_input)

    # Thêm tin nhắn từ chatbot vào cuộc hội thoại
    bot_message = ChatMessage(role=ChatMessageRole.ASSISTANT, content=final_answer.data.content)
    conversation_history[thread_id].append(bot_message)

    # Kiểm tra xem đã có bản ghi nào với thread_id và user_id chưa
    existing_history = db.query(ChatHistory).filter_by(thread_id=thread_id, user_id=user_id).first()

    if existing_history:
        # Nếu đã có, nối thêm các tin nhắn mới vào conversation hiện có
        existing_history.conversation += "\n" + "\n".join([f"{msg.role}: {msg.content}" for msg in conversation_history[thread_id]])
        db.commit()
    else:
        # Nếu chưa có, tạo một bản ghi mới
        conversation_text = "\n".join([f"{msg.role}: {msg.content}" for msg in conversation_history[thread_id]])
        db.add(ChatHistory(thread_id=thread_id, user_id=user_id, conversation=conversation_text))
        db.commit()

    logger.info(f"Toàn bộ cuộc hội thoại cho thread_id {thread_id} đã được lưu vào cơ sở dữ liệu.")

    return {
        "data": {
            "reply_message": {
                "content": str(final_answer.data.content),
                "metadata": {},
                "postback": "",
                "forward_to_cs": False
            }
        }
    }
