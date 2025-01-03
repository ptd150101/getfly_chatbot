from . import *
from langfuse.decorators import observe, langfuse_context
from utils.log_utils import get_logger
from schemas.api_response_schema import ChatLogicInputData
from .generator import VertexAIGenerator
from .chat_generator import VertexAIChatGenerator
from .enrichment import Enrichment
from .answer_generator import AnswerGenerator
from .document_retriever import DocumentRetriever
from .embedder import Embedder
from .translate import Translate
from .summary import Summary
from .spell_correct import InputValidator
from .routing_question import RoutingQuestion
from .abstract_query import AbstractQuery
from .database import get_db
from source.config.setting_bot import GETFLY_BOT_SETTINGS
import traceback
from config.env_config import (
    DEFAULT_ANSWER, CREDENTIALS_PATH,
    OVERLOAD_MESSAGE, CS_MESSAGE, NO_RELEVANT_GETFLY_MESSAGE
)
from google.oauth2.service_account import Credentials
from .single_query import SingleQuery
from .multi_query import MultiQuery
from .detect_context_string import DetectPlatform
import re

credentials = Credentials.from_service_account_file(
    CREDENTIALS_PATH,
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)

logger = get_logger(__name__)


class AI_Chatbot_Service:

    def __init__(self):
        generator_pro = VertexAIGenerator(
            # model="gemini-2.0-flash-exp",
            model="gemini-1.5-pro-002",
            project_id="communi-ai",
            location="asia-southeast1",
            credentials=credentials
            )
        generator_flash = VertexAIGenerator(
            # model="gemini-2.0-flash-exp",
            model="gemini-1.5-flash-002",
            project_id="communi-ai",
            location="asia-southeast1",
            credentials=credentials
            )
        chat_generator = VertexAIChatGenerator(
            # model="gemini-2.0-flash-exp",
            model="gemini-1.5-pro-002",
            project_id="communi-ai",
            location="asia-southeast1",
            credentials=credentials
            )
        
        chat_generator_flash = VertexAIChatGenerator(
            # model="gemini-2.0-flash-exp",
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
        self.spell_correct = InputValidator(
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
        self.single_query = SingleQuery(
            generator=generator_flash,
            max_retries=20, 
            retry_delay=2.0
        )
        self.multi_query = MultiQuery(
            generator=generator_flash,
            max_retries=20, 
            retry_delay=2.0
        )

        self.detect_platform = DetectPlatform(
            generator=generator_flash,
            max_retries=20, 
            retry_delay=2.0
        )



    @observe(name="AI_Chatbot_Service_Answer")
    async def create_response(self, user_data: ChatLogicInputData):
        langfuse_context.update_current_trace(
            user_id=user_data.user_name,
            tags=["STAGING", "GETFLY"]
        )
        try:
            original_question = user_data.content
            summary_history = user_data.summary
            corrected_question = {
                "correct_query": original_question,
                "routing": "CORRECT"
            }

            # if corrected_question.get("routing", "") == "UNCORRECT":
            #     return -202, [{"type": "text", "content": DEFAULT_ANSWER}], user_data.summary, [], DEFAULT_ANSWER

            # platform_response = await self.detect_platform.run(question=corrected_question.get('correct_query', ''))
            # platform = platform_response.get('platform', '')

            routing_question = await self.routing_question.run(corrected_question.get('correct_query', ''))
            responses = []

            # if routing_question.get("customer_service_request") is True:
            #     return 200, [{"type": "text", "content": CS_MESSAGE}], user_data.summary, [], CS_MESSAGE

            # else:
            # if routing_question.get("is_getfly_relevant", "") is False:
            #     return 200, [{"type": "text", "content": NO_RELEVANT_GETFLY_MESSAGE}], user_data.summary, [], NO_RELEVANT_GETFLY_MESSAGE

            # Tối ưu hóa logic cho việc lấy tài liệu
            relevant_documents, seen_ids = [], set()
            if routing_question.get("complexity_score", "") > 7:
                multi_query = await self.multi_query.run(user_data=user_data, question=corrected_question['correct_query'])
                child_prompts = multi_query.get('child_prompt_list', [])
                original_query = corrected_question['correct_query']
            else:
                single_query = (await self.single_query.run(user_data=user_data, question=corrected_question['correct_query'])).get("rewrite_prompt", "")
                child_prompts = [single_query]
                original_query = single_query

            for query in child_prompts:
                documents = self.document_retriever.run(query=query, threshold=0.35)
                for doc in documents['final_rerank']:
                    if doc['id'] not in seen_ids:
                        relevant_documents.append(doc)
                        seen_ids.add(doc['id'])

            if not relevant_documents:
                documents = self.document_retriever.run(query=corrected_question.get('correct_query', ''), threshold=0.35)
                for doc in documents['final_rerank']:
                    if doc['id'] not in seen_ids:
                        relevant_documents.append(doc)
                        seen_ids.add(doc['id'])

            # Gọi answer_generator với relevant_documents (có thể rỗng hoặc có dữ liệu)
            answer = await self.answer_generator.run(
                messages=user_data.histories,
                relevant_documents=sorted(relevant_documents, key=lambda doc: doc['cross_score'], reverse=False) if relevant_documents else [],
                summary_history=summary_history,
                original_query=original_question,
            )

            is_query_answerable = answer.get("is_query_answerable", "")
            if is_query_answerable is False:
                return 200, [{"type": "text", "content": DEFAULT_ANSWER}], user_data.summary, [], DEFAULT_ANSWER

            original_answer = answer.get("answer", "")
            references = answer.get("references", [])

            responses.append({
                "type": "text",
                "content": f"{self.answer_generator.format_answer(original_answer).get('answer', '')}"
            })

            # Tạo references với link nhúng
            if references:
                embedded_links = []
                parent_headers = {}  # Tạo từ điển để lưu các header cha


                def clean_link(link):
                    # Xóa phần /~/revisions/X4jWLQC5Kpi3KnYF2yLa từ link
                    cleaned_url = re.sub(r'/~/revisions/[A-Za-z0-9]+', '', link)
                    
                    return cleaned_url

                for ref in references:
                    content_lines = ref.get('page_content', '').split('\n')
                    
                    # Lấy dòng đầu tiên
                    first_line = content_lines[0].strip() if content_lines else ''
                    
                    # Tìm header cuối cùng (header có nhiều # nhất)
                    last_header = None
                    max_hash_count = 0
                    
                    for line in content_lines:
                        line = line.strip()
                        if line.startswith('#'):
                            hash_count = len(line) - len(line.lstrip('#'))
                            if hash_count >= max_hash_count:
                                max_hash_count = hash_count
                                last_header = line.lstrip('# *').rstrip('*')
                    
                    if last_header and first_line:
                        last_header = re.sub(r'\s*<a href="#undefined" id="undefined"></a>', '', last_header)
                        print("last_header: ", last_header)
                        # Xử lý first_line để lấy 2 cấp cuối cùng
                        path_parts = first_line.split('>')
                        if len(path_parts) >= 2:
                            first_line = f"{path_parts[-2].strip()} › {path_parts[-1].strip()}"
                        elif len(path_parts) == 1:
                            first_line = path_parts[0].strip()
                        
                        first_line = first_line.replace('**', '').replace('>', '›')
                        last_header = last_header.replace('**', '').replace('>', '›')
                        title = f"{first_line} › {last_header}"

                        # Gộp các header có chung parent header
                        parent_header = last_header.split(' › ')[-2] if ' › ' in last_header else None
                        if parent_header:
                            if parent_header in parent_headers:
                                parent_headers[parent_header].append(title)
                            else:
                                parent_headers[parent_header] = [title]
                        else:
                            embedded_links.append(f"[{title}]({clean_link(ref.get('child_link', ''))})")

                # Tạo chuỗi cho các header đã gộp
                for parent, titles in parent_headers.items():
                    combined_title = f"{parent} › " + " › ".join(titles)
                    link = ref.get('child_link', '')
                    if link:
                        embedded_links.append(f"[{combined_title}]({link})")

                if embedded_links:
                    references_str = "\n".join(f"- {link}" for link in embedded_links)
                    responses.append({
                        "type": "text",
                        "content": f"Xem thêm:\n{references_str}"
                    })
            



            # Xử lý phản hồi hình ảnh và video
            for doc in relevant_documents:
                if doc.get('images'):
                    responses.append({"type": "images", "content": list(set(doc['images']))})
                if doc.get('videos'):
                    responses.append({"type": "videos", "content": list(set(doc['videos']))})

            summary_history = await self.create_summary(
                messages=user_data.histories,
                previous_summary=summary_history,
                assistant_message=original_answer
            )

            user_data.summary = summary_history
            return 200, responses, summary_history, references, self.answer_generator.format_answer(original_answer).get('answer', '')

        except Exception as e:
            logger.error(f"Error in main create_response: {e}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            logger.info("No data found")
            return -202, [{"type": "text", "content": OVERLOAD_MESSAGE}], user_data.summary, [], OVERLOAD_MESSAGE



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