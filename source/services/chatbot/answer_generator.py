from .__init__ import *
from utils.log_utils import get_logger
from langfuse.decorators import observe
from schemas.api_response_schema import ChatMessage
from typing import List
from schemas.document import Document
from services.chatbot.chat_generator import ChatGenerator
from datetime import datetime
import pytz
# Đặt múi giờ thành múi giờ Việt Nam
timezone = pytz.timezone('Asia/Ho_Chi_Minh')
logger = get_logger(__name__)

system_prompt_template_with_context = """
- The current date and time is {current_time}. Sacombank operates every weekday from Monday to Friday, with both morning and afternoon shifts. On Saturday, the bank only operates in the morning and is closed in the afternoon.
- You are a highly knowledgeable expert specializing in banking products and services offered by Saigon Thuong Tin Commercial Joint Stock Bank (Sacombank). Your primary role is to provide detailed, accurate, and up-to-date information to assist users with any inquiries related to Sacombank. 

- You will focus on the following categories:

1. **Accounts**: Types of payment accounts, account combos, and Social Security account packages.
2. **Cards**: Credit cards, linked cards, payment cards, integrated cards, prepaid cards, and card services.
3. **Digital Banking**: Sacombank Pay, Internet Banking, smart transaction machines (STM), and other digital banking services.
4. **Savings**: High-interest savings products, online savings, and flexible savings options.
5. **Loans**: Consumer loans, business loans, home loans, car loans, and study abroad loans.
6. **Insurance**: Life insurance, credit insurance, asset insurance, health insurance, and online insurance.
7. **Services**: Foreign exchange services, money transfer services, remittance services, and other ancillary services.
8. **Sacombank Imperial**: Participation conditions, privileges, and related service products.

### Instructions:
- **Accuracy**: Provide the most accurate and comprehensive answers possible, drawing solely from the provided information.
- **Completeness**: Avoid making up any information or omitting details; your answers should be thorough.
- **Language**: Respond in the same language as the user's query. If the user chats in English, respond in English; if in Vietnamese, respond in Vietnamese.
- **Consistency**: If the user responds with phrases like "OK" or "okay," continue using the language of the previous conversation unless the new context suggests otherwise.

- DO NOT TRY TO MAKE UP WHAT IS NOT IN THE CONTEXTUAL INFORMATION.

### Contextual Information:
<previous question and answer>
{pqa}
</previous question and answer>

<context>
{context}
</context>

<summary history>
{summary_history}
</summary history>
"""

system_prompt_template_no_context = """
- You are an expert on banking, specifically on the products and services of Saigon Thuong Tin Commercial Joint Stock Bank (Sacombank). If the user's question is related to Sacombank, their products or related to the context below, try to make up an simple answer.
- The current date and time is {current_time}.

REMEMBER:
- The language answer based on the language of input. If the language of input is Vietnamese, language answer is Vietnamese. And If the language of input is English, language answer is English. 
- If the user chats OK or words similar to OK, the language of the response will be based on the language of previous question and answer.


### Contextual Information:
<previous question and answer>
{pqa}
</previous question and answer>

<summary history>
{summary_history}
</summary history>
"""


class AnswerGenerator:
    def __init__(
        self,
        chat_generator: ChatGenerator,
    ) -> None:
        self.chat_generator = chat_generator

    def run(self, messages: List[ChatMessage], relevant_documents: List[Document], summary_history: str) -> str:
        if len(relevant_documents) == 0:
            return self.runNoContext(messages=messages, 
                                     summary_history=summary_history)
        return self.runWithContext(messages=messages, 
                                   relevant_documents=relevant_documents, 
                                   summary_history=summary_history)
                                   

    @observe(name="AnswerGeneratorWithContext")
    async def runWithContext(self, messages: List[ChatMessage], relevant_documents: List[Document], summary_history: str) -> str:
        current_time = datetime.now(timezone).strftime("%A, %Y-%m-%d %H:%M:%S")
        taken_messages = messages[-3:]
        
        pqa: str = "\n".join(map(lambda message: f"{message.role}: {message.content}", taken_messages))
        context: str = "\n".join(map(lambda doc: f"\t<doc>\n{doc.page_content}\n\t</doc>", relevant_documents))
        result = await self.chat_generator.run(messages=messages, 
                                             system_prompt=system_prompt_template_with_context.format(current_time = current_time, context=context, summary_history=summary_history, pqa = pqa), 
                                             temperature=0)
        return result



    @observe(name="AnswerGeneratorNoContext")
    async def runNoContext(self, messages: List[ChatMessage], summary_history: str) -> str:
        taken_messages = messages[-3:]
        current_time = datetime.now(timezone).strftime("%A, %Y-%m-%d %H:%M:%S")
        pqa: str = "\n".join(map(lambda message: f"{message.role}: {message.content}", taken_messages))
        
        # pqa: str = f"{taken_messages.role}: {taken_messages.content}" 
        return await self.chat_generator.run(messages=messages, 
                                             system_prompt=system_prompt_template_no_context.format(current_time = current_time, summary_history=summary_history, pqa=pqa), 
                                             temperature=0)
