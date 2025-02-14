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
import traceback
from config.env_config import CREDENTIALS_PATH, DEFAULT_ANSWER, OVERLOAD_MESSAGE
from google.oauth2.service_account import Credentials
from .single_query import SingleQuery
from .multi_query import MultiQuery
from .detect_context_string import DetectPlatform
from .detect_language import DetectLanguage
import re
from .md2text import markdown_to_text
# from .setting import Setting

# DEFAULT_ANSWER = Setting.default_message
# OVERLOAD_MESSAGE = Setting.overload_message
# llm_model = Setting.llm_model


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
            max_retries=5, 
            retry_delay=2.0
        )
        self.enrichment = Enrichment(
            generator=generator_flash,
            max_retries=5, 
            retry_delay=2.0
        )
        self.db = next(get_db())
        self.document_retriever = DocumentRetriever(session=self.db)
        self.embedder = Embedder(
            url="http://35.197.153.145:8231/embed",
            batch_size=1,
            max_length=4096,
            max_retries=5,
            retry_delay=2.0 
        )
        self.answer_generator = AnswerGenerator(
            chat_generator=chat_generator_flash,
            )
        self.spell_correct = InputValidator(
            generator=generator_flash,
            max_retries=5, 
            retry_delay=2.0
        )
        self.routing_question = RoutingQuestion(
            generator=generator_flash,
            max_retries=5, 
            retry_delay=2.0
        )
        self.translate = Translate(
            generator=generator_flash,
            max_retries=5, 
            retry_delay=2.0
        )
        self.abstract_query = AbstractQuery(
            generator=generator_flash,
            max_retries=5, 
            retry_delay=2.0
        )
        self.single_query = SingleQuery(
            generator=generator_flash,
            max_retries=5, 
            retry_delay=2.0
        )
        self.multi_query = MultiQuery(
            generator=generator_flash,
            max_retries=5, 
            retry_delay=2.0
        )

        self.detect_platform = DetectPlatform(
            generator=generator_flash,
            max_retries=5, 
            retry_delay=2.0
        )
        self.detect_language = DetectLanguage(
            generator=generator_flash,
            max_retries=5, 
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

            language_response = await self.detect_language.run(question=original_question)
            language = language_response.get('language', '')

            # routing_question = await self.routing_question.run(corrected_question.get('correct_query', ''))
            responses = []

            # Tối ưu hóa logic cho việc lấy tài liệu
            relevant_documents, seen_ids = [], set()
            # if routing_question.get("complexity_score", "") > 8:
            #     multi_query = await self.multi_query.run(user_data=user_data, question=corrected_question['correct_query'])
            #     child_prompts = multi_query.get('child_prompt_list', [])
            #     original_query = corrected_question['correct_query']
            # else:
            single_query = (await self.single_query.run(user_data=user_data, question=original_question)).get("rewrite_prompt", "")
            if single_query:
                child_prompts = [single_query]
            else:
                child_prompts = [original_question]
            
            for query in child_prompts:
                documents = self.document_retriever.run(query=query, threshold=0.1)
                for doc in documents['final_rerank']:
                    if doc['id'] not in seen_ids:
                        relevant_documents.append(doc)
                        seen_ids.add(doc['id'])

            if not relevant_documents:
                documents = self.document_retriever.run(query=original_question, threshold=0.1)
                for doc in documents['final_rerank']:
                    if doc['id'] not in seen_ids:
                        relevant_documents.append(doc)
                        seen_ids.add(doc['id'])



            # if relevant_documents:
                # Gọi answer_generator với relevant_documents (có thể rỗng hoặc có dữ liệu)
            answer = await self.answer_generator.run(
                messages=user_data.histories,
                relevant_documents=sorted(relevant_documents, key=lambda doc: doc['cross_score'], reverse=False),
                summary_history=summary_history,
                original_query=original_question,
                language=language
            )

            if answer.get("is_query_answerable", "") == False:
                responses.append({
                    "type": "text_no_answerable",
                    "content": answer.get("answer", "")
                })
                return 200, responses, summary_history, [], answer.get("answer", "")

            # else:
            #     responses.append({
            #         "type": "text_no_relevant",
            #         "content": DEFAULT_ANSWER
            #     })
            #     return 200, responses, summary_history, [], DEFAULT_ANSWER

            # is_query_answerable = answer.get("is_query_answerable", "")
            # if is_query_answerable is False:
            #     return 200, [{"type": "text", "content": DEFAULT_ANSWER}], user_data.summary, [], DEFAULT_ANSWER

            original_answer = answer.get("answer", "")
            references = answer.get("references", [])

            responses.append({
                "type": "text",
                "content": f"{self.answer_generator.format_answer(original_answer).get('answer', '')}"
            })

            # Tạo references với link nhúng
            if references:
                embedded_links = []
                for ref in references:
                    content_lines = ref.get('page_content', '').split('\n')
                    
                    # Lấy dòng đầu tiên
                    first_line = content_lines[0].strip() if content_lines else ''
                    
                    # Tìm header cuối cùng (header có nhiều # nhất)
                    last_header = ref.get('last_header', '')
                    child_link = ref.get('child_link', '')

                    # Xử lý first_line để lấy 2 cấp cuối cùng
                    path_parts = first_line.split('>')
                    if len(path_parts) >= 2:
                        first_line = f"{path_parts[-2].strip()} › {path_parts[-1].strip()}"
                    elif len(path_parts) == 1:
                        first_line = path_parts[0].strip()
                    
                    first_line = first_line.replace('**', '').replace('>', '›')


                    if last_header:
                        last_header = re.sub(r'\s*<a href="#undefined" id="undefined"></a>', '', last_header)

                        last_header = last_header.replace('**', '').replace('>', '›')
                        if last_header.endswith(f"{first_line}"):
                            title = markdown_to_text(last_header)
                        else:
                            title = f"{first_line} › {markdown_to_text(last_header)}"
                        print("title: ", title)
                    else:
                        title = first_line
                        
                        
                        
                    embedded_links.append(f"[{title}]({child_link})")

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