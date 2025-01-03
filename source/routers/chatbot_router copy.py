from fastapi import APIRouter, Header, Request, HTTPException
from fastapi.responses import StreamingResponse
from schemas.api_response_schema import ChatLogicInputData, ChatMessageRole, ChatMessage, make_response
from source.services.chatbot.chatbot_ai import AI_Chatbot_Service
from utils.log_utils import get_logger
from .database import (
    SessionLocal, User, Thread,
    ChatHistory, ConversationCache
)
from datetime import datetime, timedelta
import os
import subprocess
import aiohttp
import asyncio
import traceback
from sqlalchemy.exc import SQLAlchemyError
import json
from sqlalchemy.orm import Session  # Thêm import này


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


RESTART_KEYWORDS = {"bắt đầu", "bắt đầu lại", "start", "bat dau lai", "bat dau", "bdl", "start again"}




async def create_answer_eng(user_data: ChatLogicInputData):
    try:
        if not user_data.content:
            logger.info("Empty Question")
            return make_response(-502, content="Empty content")
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





async def typing_message(thread_id: str, app_id: str = "1vkxsq0xau7"):
    url = f"https://{app_id}.api.piscale.com/chat-bot/v1.0/threads/{thread_id}/typing"
    payload = {}
    headers = {
    'X-PiScale-Bot-Token': '6872016403399478:DQq64DXH9D59W9xGkKLz3svlIkfZluAaAYRW6TrG'
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as response:
            return await response.json()




async def send_message_to_thread(thread_id: str, message: str, app_id: str = "1vkxsq0xau7"):
    """Gửi tin nhắn đến thread thông qua API"""
    url = f"https://{app_id}.api.piscale.com/chat-bot/v1.0/messages"
    headers = {
        'X-PiScale-Bot-Token': '6872016403399478:DQq64DXH9D59W9xGkKLz3svlIkfZluAaAYRW6TrG'
    }
    payload = {
        "thread_id": thread_id,
        "body": {
            "text": message,
            "is_rtf": True
        }
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as response:
            return await response.json()


async def handle_restart_chat(communi_thread_id: str, message: str):
    """
    Kiểm tra và xử lý yêu cầu restart chat
    """
    try:
        if message.lower().strip() in RESTART_KEYWORDS:
            db = SessionLocal()
            try:
                # Kiểm tra xem communi_thread_id đã tồn tại chưa
                existing_thread = db.query(Thread).filter(
                    Thread.communi_thread_id == communi_thread_id
                ).first()

                if existing_thread:
                    # Xóa lịch sử chat cũ từ ConversationCache
                    db.query(ConversationCache).filter(
                        ConversationCache.thread_id == existing_thread.thread_id
                    ).delete()
                    
                    # Xóa lịch sử chat cũ từ ChatHistory
                    db.query(ChatHistory).filter(
                        ChatHistory.thread_id == existing_thread.thread_id
                    ).delete()

                # Tạo thread mới với communi_thread_id và user_id (nếu có) từ thread cũ
                new_thread = Thread(
                    communi_thread_id=communi_thread_id,
                    user_id=existing_thread.user_id if existing_thread else None
                )
                db.add(new_thread)
                db.commit()
                db.refresh(new_thread)
                
                logger.info(f"""
                    Tạo thread mới:
                    - thread_id: {new_thread.thread_id}
                    - communi_thread_id: {communi_thread_id}
                    - user_id: {new_thread.user_id}
                    - từ thread cũ: {True if existing_thread else False}
                """)
                
                # Gửi tin nhắn chào mừng mới
                welcome_message = "Chào bạn, mình là Getfly Pro - một trợ lý ảo của Getfly. Mình có thể giúp gì cho bạn?"
                await send_message_to_thread(communi_thread_id, welcome_message)
                
                # Khởi tạo conversation history mới cho thread_id này trong database
                welcome_history = [{
                    "role": ChatMessageRole.ASSISTANT,
                    "content": welcome_message
                }]
                await save_conversation_history(db, new_thread.thread_id, welcome_history)
                
                logger.info(f"Đã khởi tạo chat mới với thread_id: {new_thread.thread_id}")

                return True, {
                    "data": [{
                        "reply_message": {
                            "content": welcome_message,
                            "metadata": [],
                            "postback": "",
                            "forward_to_cs": False
                        }
                    }]
                }
            finally:
                db.close()
                
    except Exception as e:
        logger.error(f"Lỗi khi restart chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    return False, None


async def send_rating_message(thread_id: str, app_id: str = "1vkxsq0xau7"):
    """
    Gửi tin nhắn mời đánh giá với quick reply
    """
    url = f"https://{app_id}.api.piscale.com/chat-bot/v1.0/messages"
    headers = {
        'X-PiScale-Bot-Token': '6872016403399478:DQq64DXH9D59W9xGkKLz3svlIkfZluAaAYRW6TrG'
    }
    text = """Getfly Chatbot rất vui được hỗ trợ Bạn và hy vọng sớm gặp lại Bạn trong thời gian tới.
Để nâng cao chất lượng dịch vụ, Getfly rất mong nhận được ý kiến góp ý của Bạn. Bạn vui lòng dành ít phút đánh giá chất lượng hỗ trợ của Getfly Chatbot theo mức độ hài lòng với thang điểm từ 1⭐️ đến 5⭐️ theo danh mục dưới đây:
"""
    payload = {
        "thread_id": thread_id,
        "body": {
            "text": text,
            "metadata": [
                {
                    "type": "quick_reply",
                    "quick_reply": {
                        "items": [
                            {
                                "label": "5⭐",
                                "action": {
                                    "type": 2,
                                    "payload": "rating_5"
                                }
                            },
                            {
                                "label": "4⭐",
                                "action": {
                                    "type": 2,
                                    "payload": "rating_4"
                                }
                            },
                            {
                                "label": "3⭐",
                                "action": {
                                    "type": 2,
                                    "payload": "rating_3"
                                }
                            },
                            {
                                "label": "2⭐",
                                "action": {
                                    "type": 2,
                                    "payload": "rating_2"
                                }
                            },
                            {
                                "label": "⭐",
                                "action": {
                                    "type": 2,
                                    "payload": "rating_1"
                                }
                            }
                        ]
                    }
                }
            ]
        }
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as response:
            return await response.json()

rating_tasks = {}
async def check_and_send_rating(thread_id: str, communi_thread_id: str):
    """
    Background task để kiểm tra và gửi rating sau 10 giây
    """
    try:
        db = SessionLocal()
        try:
            thread = db.query(Thread).filter(Thread.thread_id == thread_id).first()
            if not thread:
                return

            # Lấy conversation history để đếm số messages
            conversation_history = await get_conversation_history(db, thread.thread_id)
            total_messages = len(conversation_history)


            # Tính số cặp hỏi đáp từ lần rating trước
            messages_since_rating = thread.message_pairs_count
            if thread.last_rating_sent:
                # Nếu đã từng gửi rating, lấy số cặp hỏi đáp từ lần gửi rating gần nhất
                messages_since_rating = thread.message_pairs_count - thread.last_rating_count
            
            # Tính thời gian từ câu trả lời cuối của bot
            time_since_last_response = 0
            if thread.last_bot_response:
                time_since_last_response = (datetime.now() - thread.last_bot_response).total_seconds()

            logger.info(f"""
                Kiểm tra điều kiện gửi rating:
                - Total messages: {total_messages}
                - Messages since last rating: {messages_since_rating}
                - Time since last response: {time_since_last_response}
                - Last rating sent: {thread.last_rating_sent}
            """)

            # Chỉ gửi rating khi:
            # 1. Có ít nhất 6 messages (3 cặp hỏi đáp)
            # 2. Có ít nhất 3 cặp hỏi đáp (từ đầu nếu chưa gửi rating, hoặc từ lần rating trước)
            # 3. Đã 10 giây từ câu trả lời cuối của bot
            if total_messages >= 6 and messages_since_rating >= 3 and time_since_last_response >= 180:
                logger.info("Đang gửi rating message...")
                rating_response = await send_rating_message(communi_thread_id)
                
                if rating_response and rating_response.get("message_code") == "M200":
                    logger.info("Gửi rating thành công")
                    thread.last_rating_sent = datetime.now()
                    thread.last_rating_count = thread.message_pairs_count  # Lưu lại số cặp hỏi đáp tại thời điểm gửi rating
                    db.commit()
                else:
                    logger.error(f"Gửi rating thất bại: {rating_response}")
            else:
                logger.info("Chưa đủ điều kiện gửi rating")
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Lỗi trong background task check_and_send_rating: {str(e)}")
    finally:
        if thread_id in rating_tasks:
            del rating_tasks[thread_id]



async def get_conversation_history(db: Session, thread_id: int) -> list:
    """Lấy conversation history từ database"""
    cache = db.query(ConversationCache).filter(
        ConversationCache.thread_id == thread_id
    ).first()
    
    if cache:
        return json.loads(cache.conversation_data)
    return []

async def save_conversation_history(db: Session, thread_id: int, history: list):
    """Lưu conversation history với proper transaction"""
    try:
        cache = db.query(ConversationCache).filter(
            ConversationCache.thread_id == thread_id
        ).with_for_update().first()  # Add lock
        
        if cache:
            cache.conversation_data = json.dumps(history)
            cache.updated_at = datetime.now()
        else:
            cache = ConversationCache(
                thread_id=thread_id,
                conversation_data=json.dumps(history)
            )
            db.add(cache)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error when saving history: {str(e)}")
        raise


async def connect_to_cs_team(thread_id: str, app_id: str = "1vkxsq0xau7"):
    """
    Kết nối với team CSKH thông qua API
    """
    try:
        url = f"https://{app_id}.api.piscale.com/conversation-navigator/v1.0/manage"
        
        headers = {
            'X-PiScale-Bot-Token': '6872016403399478:DQq64DXH9D59W9xGkKLz3svlIkfZluAaAYRW6TrG',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "proactively": 2,
            "state": 1,
            "thread_id": thread_id
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{url}?api_key=fa1b865d9280d4a488afa30fd60216e7",
                headers=headers,
                json=payload
            ) as response:
                result = await response.json()
                logger.info(f"Kết quả kết nối CSKH: {result}")
                return result
                
    except Exception as e:
        logger.error(f"Lỗi khi kết nối với team CSKH: {str(e)}")
        raise


async def handle_chat(communi_thread_id: str, message: str):
    """
    Xử lý tin nhắn chat thông thường
    """
    try:
        db = SessionLocal()
        try:
            # Lấy thread hiện tại dựa vào communi_thread_id
            thread = db.query(Thread).filter(Thread.communi_thread_id == communi_thread_id).first()
            if not thread:
                logger.info(f"Thread not found, creating new thread for communi_thread_id: {communi_thread_id}")
                # Tạo thread mới
                thread = Thread(
                    communi_thread_id=communi_thread_id,
                )
                try:
                    db.add(thread)
                    db.commit()
                    db.refresh(thread)
                    logger.info(f"Created new thread with ID: {thread.thread_id}")
                except SQLAlchemyError as e:
                    logger.error(f"Database error when creating new thread: {str(e)}")
                    db.rollback()
                    raise HTTPException(status_code=500, detail="Failed to create thread")

            # Bắt đầu typing effect
            await typing_message(communi_thread_id)
            async def typing_loop():
                while True:
                    await asyncio.sleep(2)
                    await typing_message(thread.communi_thread_id)

            typing_task = asyncio.create_task(typing_loop())

            try:
                # Lấy thông tin user
                user_id = thread.user_id
                user = db.query(User).filter(User.user_id == user_id).first()
                user_name = user.display_name if user else ""

                existing_history = db.query(ChatHistory).filter_by(thread_id=thread.thread_id, user_id=user_id).first()

                # Lấy conversation history từ database
                conversation_history = await get_conversation_history(db, thread.thread_id)
                
                # Khởi tạo conversation history nếu chưa có
                if not conversation_history:
                    # Thêm tin nhắn chào mừng
                    welcome_message = {
                        "role": ChatMessageRole.ASSISTANT,
                        "content": "Chào bạn, mình là Getfly Pro - một trợ lý ảo của Getfly. Mình có thể giúp gì cho bạn?"
                    }
                    conversation_history = [welcome_message]
                    await save_conversation_history(db, thread.thread_id, conversation_history)
                    logger.info(f"Khởi tạo lịch sử chat cho thread_id {thread.thread_id}")

                # Thêm tin nhắn người dùng vào history
                user_message = {
                    "role": ChatMessageRole.USER,
                    "content": message
                }
                conversation_history.append(user_message)
                await save_conversation_history(db, thread.thread_id, conversation_history)

                # Log để debug
                logger.info(f"""
                    Chat history for thread {thread.thread_id}:
                    Total messages: {len(conversation_history)}
                    Last message: {conversation_history[-1]['content']}
                """)

                # Tạo input cho AI
                chat_logic_input = ChatLogicInputData(
                    thread_id=str(thread.thread_id),
                    content=message,
                    histories=[ChatMessage(**msg) for msg in conversation_history],
                    user_id=str(user_id),
                    user_name=user_name,
                )

                # Lấy câu trả lời từ AI
                final_answer = await create_answer_eng(chat_logic_input)

                # Xử lý response và gửi tin nhắn
                for response in final_answer.data.content:
                    if response["type"] == "text":
                        # Gửi tin nhắn
                        await send_message_to_thread(communi_thread_id, response["content"])
                        typing_task.cancel()

                        # Cập nhật conversation history
                        bot_message = {
                            "role": ChatMessageRole.ASSISTANT,
                            "content": response["content"]
                        }
                        conversation_history.append(bot_message)
                        await save_conversation_history(db, thread.thread_id, conversation_history)

                        # Cập nhật DB
                        if existing_history:
                            existing_history.conversation += "\n" + "\n".join([
                                f"{msg['role']}: {msg['content']}" 
                                for msg in conversation_history
                            ])
                            existing_history.display_name = user_name
                            existing_history.created_at = datetime.now()
                        else:
                            conversation_text = "\n".join([
                                f"{msg['role']}: {msg['content']}" 
                                for msg in conversation_history
                            ])
                            db.add(ChatHistory(
                                thread_id=thread.thread_id,
                                user_id=user_id,
                                display_name=user_name,
                                conversation=conversation_text,
                                created_at=datetime.now()
                            ))
                    # elif response["type"] == "quick_reply":
                    #     await send_message_to_thread(communi_thread_id, response["content"])
                    #     return True, {"status": "success", "message": "Message sent"}
                # Cập nhật thread
                thread.message_pairs_count += 1
                thread.last_bot_response = datetime.now()
                db.commit()

                # Tạo task để gửi rating sau 10s
                thread_id = str(thread.thread_id)
                if thread_id in rating_tasks:
                    rating_tasks[thread_id].cancel()
                task = asyncio.create_task(check_and_send_rating(thread_id, communi_thread_id))
                rating_tasks[thread_id] = task



                return True, {"status": "success", "message": "Message sent"}

            finally:
                typing_task.cancel()
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Lỗi khi xử lý tin nhắn: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))





@chat_router.post("/")
async def webhook_handler(request: Request):
    
    """Xử lý webhook và gửi tin nhắn phản hồi nếu là lệnh restart"""
    try:
        # Parse webhook payload
        json_data = await request.json()
        logger.info(f"Webhook payload: {json.dumps(json_data, ensure_ascii=False, indent=2)}")

        # Lấy nội dung tin nhắn và communi_thread_id
        message = json_data.get("body", {}).get("text", "").lower().strip()
        communi_thread_id = json_data.get("thread_id")  # Đây chính là communi_thread_id
        if not communi_thread_id:
            logger.error("Missing thread_id in webhook payload")
            return {"error": "Missing thread_id"}
        
        
        
        
        db = SessionLocal()
        try:
            thread = db.query(Thread).filter(Thread.communi_thread_id == communi_thread_id).first()
            if thread and str(thread.thread_id) in rating_tasks:
                rating_tasks[str(thread.thread_id)].cancel()
                del rating_tasks[str(thread.thread_id)]
        finally:
            db.close()


        # Xử lý postback từ quick reply rating
        if "body" in json_data and "postback" in json_data["body"]:
            postback = json_data["body"]["postback"]
            if postback == "connect_cs_team":
                try:
                    await connect_to_cs_team(communi_thread_id)
                    return {"status": "success", "message": "Connected to CSKH"}
                except Exception as e:
                    logger.error(f"Lỗi khi xử lý yêu cầu kết nối CSKH: {str(e)}")
                    await send_message_to_thread(
                        communi_thread_id,
                        "Xin lỗi, hiện tại không thể kết nối tới bộ phận CSKH. Vui lòng thử lại sau."
                    )
                    return {"status": "error", "message": "Failed to connect to CSKH"}
            elif postback.startswith("rating_"):
                try:
                    rating = int(postback.split("_")[1])

                    # Lấy thông tin user
                    sender = json_data.get("sender", {})
                    display_name = sender.get("display_name", "Unknown")
                    user_id = sender.get("ext_user_id", "Unknown")



                    db = SessionLocal()
                    try:
                        thread = db.query(Thread).filter(
                            Thread.communi_thread_id == communi_thread_id
                        ).first()
                        
                        if thread:
                            thread.rating = rating
                            thread.rated_at = datetime.now()
                            db.commit()
                            
                            db.commit()

                            await send_message_to_thread(
                                communi_thread_id, 
                                f"Cảm ơn bạn đã đánh giá, Getfly sẽ luôn nỗ lực để nâng cao chất lượng dịch vụ. Nếu bạn cần thêm thông tin hay có thắc mắc gì, mình luôn sẵn sàng hỗ trợ 🥰🥰"
                            )



                            # Gửi thông báo đến thread admin
                            admin_message = f"**Khách hàng:** {display_name}(ID: {user_id})\n**ThreadID:** {thread.communi_thread_id}\n**Đánh giá:** {rating} ⭐"
                            await send_message_to_thread(
                                "57480069214764", 
                                admin_message
                            )

                            return {"status": "success", "message": "Rating recorded"}
                    finally:
                        db.close()
                except Exception as e:
                    logger.error(f"Lỗi khi xử lý đánh giá: {str(e)}")

        # Kiểm tra xem có ảnh trong payload không
        if "metadata" in json_data.get("body", {}) and json_data["body"]["metadata"]:
            logger.info("Người dùng đã gửi ảnh.")
            # Nếu có văn bản, chỉ xử lý văn bản và bỏ qua hình ảnh
            if message:
                logger.info(f"Đã nhận văn bản: {message}. Bỏ qua hình ảnh.")
            else:
                await send_message_to_thread(
                    communi_thread_id,
                    "Mình không thể xử lý hình ảnh, video, file. Vui lòng chỉ gửi văn bản."
                    )
                # Nếu không có văn bản, bạn có thể xử lý ảnh ở đây nếu cần
                return {"status": "success", "message": "Image received, but no text to process."}

        # Nếu không có ảnh hoặc có văn bản, tiếp tục xử lý tin nhắn
        is_restart, response = await handle_restart_chat(communi_thread_id, message)
        if is_restart:
            logger.info(f"Đã restart chat cho communi_thread_id: {communi_thread_id}")
            return response
        else:
            interrupt = int(json_data.get("interrupt", 0)) 
            if interrupt == 0:
                await handle_chat(communi_thread_id, message)

        return {"status": "success", "message": "Webhook received"}

    except Exception as e:
        logger.error(f"Lỗi khi xử lý webhook: {str(e)}")
        return {"error": str(e)}