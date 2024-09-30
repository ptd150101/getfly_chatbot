from . import *
from config.env_config import OPENAI_API_KEY, OPENAI_BASE_URL
from langfuse.decorators import observe
from utils.log_utils import get_logger
from schemas.api_response_schema import ChatLogicInputData, ChatMessage, ChatMessageRole
from .generator import VertexAIGenerator
from .chat_generator import VertexAIChatGenerator
from .enrichment import Enrichment
from .answer_generator import AnswerGenerator
from .document_retriever import DocumentRetriever
from .answer_generator import AnswerGenerator
from .embedder import Embedder
from .summary import Summary
import sys
from pathlib import Path

logger = get_logger(__name__)


class AI_Chatbot_Service:

    def __init__(self):
        generator = VertexAIGenerator(model="gemini-1.5-pro-001", project_id="communi-intern-ai", location="us-central1")
        chat_generator = VertexAIChatGenerator(model="gemini-1.5-pro-001", project_id="communi-intern-ai", location="us-central1")
        self.summary = Summary(generator=generator)
        self.enrichment = Enrichment(generator=generator, summary=self.summary)
        self.document_retriever = DocumentRetriever()
        self.embedder = Embedder(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
        self.answer_generator = AnswerGenerator(chat_generator=chat_generator)
    @observe(name="AI_Chatbot_Service_Answer")
    async def create_response(self, user_data: ChatLogicInputData):
        try:
            original_question = user_data.content
            summary_history = user_data.summary
            
            query = await self.enrichment.run(user_data=user_data, question=original_question)
            if query == "Bye":
                answer = await self.answer_generator.run(messages=user_data.histories, relevant_documents=[], summary_history=summary_history)
            elif query == "False":
                answer = "Tôi xin lỗi, tôi chỉ trả lời những câu hỏi liên quan đến Sacombank."
            else:
                query_embbeding = self.embedder.run(query)
                relevant_documens = self.document_retriever.run(query=query, query_embbedding=query_embbeding)
                
                answer = await self.answer_generator.run(messages=user_data.histories, relevant_documents=relevant_documens, summary_history=summary_history)
            
            # if answer.startswith("Hmm, I'm not sure."):
                # answer = await self.answer_generator.run(messages=user_data.histories, relevant_documents=[], summary_history=summary_history)
            print("Sum: "+ user_data.summary)
            return 200, answer, summary_history
            # context_relevant = await self.check_context_relevant.run(question=query, relevant_documents=relevant_documens)
            # if context_relevant:
            #     answer = await self.answer_generator.run(messages=user_data.histories+[ChatMessage(content=user_data.content, role=ChatMessageRole.USER)], relevant_documents=relevant_documens)
            #     return 200, answer
            # else:
            #     answer = await self.answer_generator.run(messages=user_data.histories+[ChatMessage(content=user_data.content, role=ChatMessageRole.USER)], relevant_documents=[])
            #     return 200, answer
        except Exception as e:
            logger.error(f"Error in main create_response: {e}")
            logger.info("No data found")
            return -202, "Failed", user_data.summary

    @observe(name="AI_Chatbot_Service_Summary")
    async def create_summary(self, user_data: ChatLogicInputData):
        try:
            summary = await self.summary.run(user_data.histories)
            return summary
        except Exception as e:
            logger.error(f"Error in main create_summary: {e}")
            logger.info("No data found")
            return  ""