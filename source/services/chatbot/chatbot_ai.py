from . import *
from langfuse.decorators import observe, langfuse_context
from utils.log_utils import get_logger
from schemas.api_response_schema import ChatLogicInputData
from .generator import VertexAIGenerator
from .chat_generator import VertexAIChatGenerator
from .enrichment import Enrichment
from .answer_generator import AnswerGenerator
from .document_retriever import DocumentRetriever
from .answer_generator import AnswerGenerator
from .embedder import Embedder
from .translate import Translate
from .summary import Summary
from .spell_correct import SpellCorrect
from .routing_question import RoutingQuestion
from .abstract_query import AbstractQuery
from .database import get_db
from source.config.setting_bot import GETFLY_BOT_SETTINGS
import traceback
from config.env_config import DEFAULT_ANSWER, CREDENTIALS_PATH
from google.oauth2.service_account import Credentials
import json


credentials = Credentials.from_service_account_file(
    CREDENTIALS_PATH,
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)

logger = get_logger(__name__)


class AI_Chatbot_Service:

    def __init__(self):
        generator_pro = VertexAIGenerator(
            model="gemini-1.5-pro-002",
            project_id="communi-ai",
            location="asia-southeast1",
            credentials=credentials
            )
        generator_flash = VertexAIGenerator(
            model="gemini-1.5-flash-002",
            project_id="communi-ai",
            location="asia-southeast1",
            credentials=credentials
            )
        chat_generator = VertexAIChatGenerator(
            model="gemini-1.5-pro-002",
            project_id="communi-ai",
            location="asia-southeast1",
            credentials=credentials
            )
        
        chat_generator_flash = VertexAIChatGenerator(
            model="gemini-1.5-flash-002",
            project_id="communi-ai",
            location="asia-southeast1",
            credentials=credentials
            )

        self.summary = Summary(
            generator=generator_flash,
            max_retries=10, 
            retry_delay=2.0
        )
        self.enrichment = Enrichment(
            generator=generator_flash,
            max_retries=10, 
            retry_delay=2.0
        )
        self.db = next(get_db())
        self.document_retriever = DocumentRetriever(session=self.db)
        self.embedder = Embedder(
            url="http://35.197.153.145:8231/embed",
            batch_size=1,
            max_length=4096,
            max_retries=20,
            retry_delay=2.0 
        )
        self.answer_generator = AnswerGenerator(
            chat_generator=chat_generator_flash,
            settings=GETFLY_BOT_SETTINGS
            )
        self.spell_correct = SpellCorrect(
            generator=generator_flash,
            max_retries=20, 
            retry_delay=2.0
        )
        self.routing_question = RoutingQuestion(
            generator=generator_flash,
            max_retries=20, 
            retry_delay=2.0
        )
        self.translate = Translate(
            generator=generator_flash,
            max_retries=20, 
            retry_delay=2.0
        )
        self.abstract_query = AbstractQuery(
            generator=generator_flash,
            max_retries=20, 
            retry_delay=2.0
        )

    @observe(name="AI_Chatbot_Service_Answer")
    async def create_response(self, user_data: ChatLogicInputData):
        langfuse_context.update_current_trace(
            user_id=user_data.user_name,  # Assuming user_data contains a user_id attribute
            tags=["STAGING", "GETFLY"]
        )
        try:
            original_question = user_data.content
            summary_history = user_data.summary
            corrected_question = json.loads(await self.spell_correct.run(user_data=user_data, question=original_question))
            if corrected_question['routing'] == "UNCORRECT":
                responses = []
                responses.append({
                    "type": "text",
                    "content": DEFAULT_ANSWER
                })
                return -202, responses, user_data.summary


            else:
                enrichment_query = await self.enrichment.run(user_data=user_data, question=corrected_question['correct_query'])
                enrichment_query = json.loads(enrichment_query)
                routing_query = enrichment_query.get('routing', '')
                relevant_documents = []
                seen_ids = set()
                original_backup_documents = []
                parent_prompt = ""
                backup_documents = []

                
                if routing_query == "RAG":
                    abstract_query = await self.abstract_query.run(corrected_question['correct_query'])


                    parent_prompt = enrichment_query.get('parent_prompt', '').strip()
                    child_prompts = enrichment_query.get('child_prompt_list', [])
                    child_prompts.append(parent_prompt)
                    child_prompts.append(abstract_query)
                    for query in child_prompts:  # Lặp qua từng câu hỏi trong danh sách querys
                        documents = self.document_retriever.run(query=query, threshold=0.35)
                        final_documents = documents['final_rerank']
                        backup_documents = documents['backup_rerank']


                        for doc in final_documents:
                            if doc['id'] not in seen_ids:
                                relevant_documents.append(doc)
                                seen_ids.add(doc['id'])


                    if relevant_documents == []:
                        documents = self.document_retriever.run(query=corrected_question['correct_query'], threshold=0.35)
                        final_documents = documents['final_rerank']
                        original_backup_documents = documents['backup_rerank']
                        for doc in final_documents:
                            if doc['id'] not in seen_ids:
                                relevant_documents.append(doc)
                                seen_ids.add(doc['id'])

                    if relevant_documents == []:
                        for doc in backup_documents + original_backup_documents:
                            if doc['id'] not in seen_ids:
                                relevant_documents.append(doc)
                                seen_ids.add(doc['id'])
                    

                # Gọi answer_generator với relevant_documents (có thể rỗng hoặc có dữ liệu)
                answer = await self.answer_generator.run(
                    messages=user_data.histories,
                    relevant_documents=sorted(relevant_documents, key=lambda doc: doc['cross_score'], reverse=True) if relevant_documents else [],
                    summary_history=summary_history,
                    original_query=corrected_question['correct_query'],
                    transform_query=parent_prompt if parent_prompt else corrected_question['correct_query']
                )
                
                text_answer = self.answer_generator.format_answer(answer)



                responses = []
                
                # 1. Text response
                text_response = {
                    "type": "text",
                    "content": text_answer
                }
                responses.append(text_response)

                # 2. Images response (nếu có)
                seen_images = set()
                images = []
                for doc in relevant_documents:
                    if doc.get('images'):
                        for img in doc['images']:
                            if img not in seen_images:
                                images.append(img)
                                seen_images.add(img)
                if images:
                    responses.append({
                        "type": "images",
                        "content": images
                    })

                # 3. Videos response (nếu có)
                seen_videos = set()
                videos = []
                for doc in relevant_documents:
                    if doc.get('videos'):
                        for video in doc['videos']:
                            if video not in seen_videos:
                                videos.append(video)
                                seen_videos.add(video)
                if videos:
                    responses.append({
                        "type": "videos",
                        "content": videos
                    })

                summary_history = await self.create_summary(
                    messages=user_data.histories,
                    previous_summary=summary_history,
                    assistant_message=text_answer
                )

                user_data.summary = summary_history
                # Trả về array của responses
                return 200, responses, summary_history



                

        except Exception as e:
            logger.error(f"Error in main create_response: {e}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            logger.info("No data found")
            responses = []
            responses.append({
                "type": "text",
                "content": "Hệ thống hiện đang quá tải, vui lòng thử lại sau"
            })
            return -202, responses, user_data.summary



    @observe(name="AI_Chatbot_Service_Summary")
    async def create_summary(self, messages, previous_summary, assistant_message):
        try:
            summary = await self.summary.run(messages=messages, 
                                        previous_summary=previous_summary,
                                        assistant_message=assistant_message)
            return summary
        except Exception as e:
            logger.error(f"Error in main create_summary: {e}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            logger.info("No data found")
            return ""