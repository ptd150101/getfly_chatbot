from langfuse.decorators import observe
from utils.log_utils import get_logger
from schemas.api_response_schema import ChatMessage
from typing import List
from .generator import Generator

logger = get_logger(__name__)

summary_prompt = """\
Given the following data, based on the conversation between the user and assistant, and the previous summary chat between them, summary this into a paragraph.

REMEMBER:
1. Focus on the key topics and requests made by the user.
2. Highlight any specific actions or solutions provided by the chatbot.
3. Note any follow-up questions or unresolved issues mentioned in the conversation.
4. Ensure the summary is clear and easy to understand, avoiding any technical jargon unless necessary.

Conversation and Previous summary chat: 
{data}
Summary paragraph:
"""


class Summary:
    def __init__(
        self,
        generator: Generator,
    ) -> None:
        self.generator = generator

    @observe(name="Summary")
    async def run(self, data) -> str:
        if isinstance(data, str):
            summary: str = await self.generator.run(
                prompt=summary_prompt.format(data=data), temperature=1.0
            )
        else:
            input_data: str = "\n".join(map(lambda d: f"{d.role}: {d.content}", data))
            summary: str = await self.generator.run(
                prompt=summary_prompt.format(data=input_data), temperature=1.0
            )
        return summary
