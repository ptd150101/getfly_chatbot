from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from schemas.api_response_schema import ChatLogicInputData, ChatMessageRole, ChatMessage, make_response
from source.services.chatbot.chatbot_ai import AI_Chatbot_Service
from utils.log_utils import get_logger
from .database import SessionLocal, User, Thread, ChatHistory  # Import từ file database.py
from datetime import datetime, timedelta
import json
import os
import subprocess
import aiohttp
import asyncio



THUMBNAIL_DIR = "static/thumbnails"
os.makedirs(THUMBNAIL_DIR, exist_ok=True)

logger = get_logger(__name__)
chat_router = APIRouter()


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
        status_code, chatbot_answer, summary_history, references, original_answer = await ai_chatbot.create_response(user_data)

        final_answer = make_response(
            status_code, 
            content=chatbot_answer, 
            summary_history=summary_history, 
            references=references, 
            original_answer=original_answer
        )
        # logger.info(f"Final answer: {final_answer}")

    except Exception as e:
        chatbot_answer = f"Error in logic function: {e}"
        final_answer = make_response(
            -503, 
            content=[{"type": "text", "content": chatbot_answer}], 
            summary_history="", 
            references=[], 
            original_answer=""
        )
    return final_answer


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
            user_name = existing_user.display_name
        else:
            # Nếu chưa tồn tại thì thêm mới
            user = User(user_id=user_data['id'], display_name=user_data['display_name'])
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"user_id {user_data['id']} đã được thêm vào cơ sở dữ liệu.")
            user_id = user.user_id  # Sử dụng user_id từ bảng users
            user_name = user.display_name
        # Tạo một bản ghi thread mới với đúng user_id từ bảng users
        new_thread = Thread(
            user_id=user_id, 
            communi_thread_id=user_data['communi_thread_id']
        )
        db.add(new_thread)
        db.commit()
        db.refresh(new_thread)
        
        logger.info(f"Thread được tạo với thread_id: {new_thread.thread_id}")
        
    
    
    # Thêm tin nhắn từ chatbot vào histories
    assistant_message = ChatMessage(role=ChatMessageRole.ASSISTANT, content="Chào bạn, tôi là Getfly Pro - một trợ lý ảo của Getfly. Tôi có thể giúp gì cho bạn?")
    histories.append(assistant_message)
    
    return {
        "data": {
            "thread": {"id": new_thread.thread_id},
            "hello_message": {
                "content": assistant_message.content  # Lấy nội dung từ assistant_message
            }
        }
    }


def generate_thumbnail(video_url, output_path):
    # Lấy frame tại giây thứ 1 của video
    command = f'ffmpeg -i {video_url} -ss 00:00:01.000 -vframes 1 {output_path}'
    subprocess.call(command, shell=True)




async def typing_message(thread_id: str, app_id: str = "1vkxsq0xau7"):
    url = f"https://{app_id}.api.piscale.com/chat-bot/v1.0/threads/{thread_id}/typing"
    payload = {}
    headers = {
    'X-PiScale-Bot-Token': '6872016403399478:DQq64DXH9D59W9xGkKLz3svlIkfZluAaAYRW6TrG'
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as response:
            return await response.json()



@chat_router.post("/threads/{thread_id}/chat")
async def post_thread_chat(thread_id: int, request: dict):
    global conversation_history

    try:
        db = SessionLocal()

        # Lấy thông tin user_id từ thread
        thread = db.query(Thread).filter(Thread.thread_id == thread_id).first()
        if not thread:
            return {"data": {"error": "Thread not found"}}

        print("thread.communi_thread_id: ", thread.communi_thread_id)
        await typing_message(thread.communi_thread_id)

        async def typing_loop():
            while True:
                await asyncio.sleep(3)
                await typing_message(thread.communi_thread_id)
        
        
        typing_task = asyncio.create_task(typing_loop())


        user_id = thread.user_id  # Lấy user_id từ thread
        user = db.query(User).filter(User.user_id == user_id).first()
        user_name = user.display_name if user else ""  # Lấy display_name từ bảng User


        # Lấy summary từ DB nếu có
        existing_history = db.query(ChatHistory).filter_by(thread_id=thread_id, user_id=user_id).first()
        summary = existing_history.summary if existing_history else ""


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
            user_id=str(user_id),
            user_name=user_name,
            summary=summary
        )
        



        final_answer = await create_answer_eng(chat_logic_input)


        responses = []

        # Xử lý text response
        for response in final_answer.data.content:
            if response["type"] == "text":
                # Cập nhật DB và conversation history
                bot_message = ChatMessage(
                    role=ChatMessageRole.ASSISTANT, 
                    content=response["content"]
                )
                if "Xem thêm" not in response["content"]:
                    conversation_history[thread_id].append(bot_message)

                if existing_history:
                    existing_history.conversation += "\n" + "\n".join([f"{msg.role}: {msg.content}" for msg in conversation_history[thread_id]])
                    existing_history.summary = final_answer.data.summary_history
                    existing_history.display_name = user_name
                    existing_history.created_at = datetime.now()
                    db.commit()
                else:
                    conversation_text = "\n".join([f"{msg.role}: {msg.content}" for msg in conversation_history[thread_id]])
                    db.add(ChatHistory(
                        thread_id=thread_id,
                        user_id=user_id,
                        display_name=user_name,
                        conversation=conversation_text,
                        summary=final_answer.data.summary_history,
                        created_at=datetime.now()
                    ))
                    db.commit()


                responses.append({
                    "reply_message": {
                        "content": str(response["content"]),
                        "metadata": [],
                        "postback": "",
                        "forward_to_cs": False
                    }
                })

        # Xử lý images response
        for response in final_answer.data.content:
            if response["type"] == "images":
                metadata = []
                for idx, image_url in enumerate(response["content"], 1):
                    metadata.append({
                        "name": f"img_{idx}.png",
                        "width": 1000,
                        "height": 1000,
                        "source_url": image_url,
                        "source_thumb_url": image_url,
                        "size": 121200,
                        "type": "image"
                    })
                responses.append({
                    "reply_message": {
                        "content": "Hình ảnh",
                        "metadata": metadata,
                        "postback": "",
                        "forward_to_cs": False
                    }
                })

        # Xử lý videos response
        for response in final_answer.data.content:
            if response["type"] == "videos":
                metadata = []
                for idx, video_url in enumerate(response["content"], 1):
                    # Tạo thumbnail cho video
                    thumbnail_filename = f"thumbnail_{thread_id}_{idx}.jpg"
                    thumbnail_path = os.path.join(THUMBNAIL_DIR, thumbnail_filename)
                    try:
                        generate_thumbnail(video_url, thumbnail_path)
                        # Tạo URL cho thumbnail (giả sử server của bạn serve static files từ thư mục static)
                        thumbnail_url = f"/static/thumbnails/{thumbnail_filename}"
                    except Exception as e:
                        logger.error(f"Error generating thumbnail: {e}")
                        thumbnail_url = video_url  # Fallback to video URL if thumbnail generation fails

                    metadata.append({
                        "name": f"video_{idx}.mp4",
                        "width": 1080,
                        "height": 1920,
                        "src_thumb_url": thumbnail_url,
                        "src_url": video_url,
                        "size": 4170635,
                        "type": "video"
                    })
                responses.append({
                    "reply_message": {
                        "content": "Video",
                        "metadata": metadata,
                        "postback": "",
                        "forward_to_cs": False
                    }
                })

        typing_task.cancel()
        return {"data": responses}
    except Exception as e:
        typing_task.cancel()
        raise e