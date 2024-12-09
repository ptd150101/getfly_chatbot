import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from langfuse.decorators import observe
import asyncio
from schemas.api_response_schema import ChatMessage, ChatMessageRole
from typing import Optional, List
import vertexai
from vertexai.generative_models import GenerativeModel, Part, Content, FinishReason
import vertexai.preview.generative_models as generative_models

# ID dự án Google Cloud
my_project = "communi-ai"

# Cấu hình tạo nội dung
generation_config = {
    "max_output_tokens": 8192,
    "temperature": 0,
    "top_p": 0.95,
}

# Cấu hình an toàn
safety_settings = {
    generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
}

class ChatGenerator:
    async def run(
        self,
        messages: List[ChatMessage],
        system_prompt: Optional[str],
        temperature: Optional[float],
    ) -> str:
        pass

class VertexAIChatGenerator(ChatGenerator):
    def __init__(
        self,
        model: str,
        credentials: str,
        project_id: str = "communi-ai",
        location: str = "asia-southeast1",
    ) -> None:
        vertexai.init(project=project_id, location=location, credentials=credentials)
        self.model_name = model

    @observe(name="VertexAIChatGenerator", as_type="generation")
    async def run(
        self,
        messages: List[ChatMessage],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        
        model = GenerativeModel(
            model_name=self.model_name, system_instruction=system_prompt
        )
        history: List[Content] = []
        for message in messages[1:]:
            if message.role == ChatMessageRole.USER:
                part = Part.from_text(message.content)  
                history += [Content(parts=[part], role="user")]
            elif message.role == ChatMessageRole.ASSISTANT:
                part = Part.from_text(message.content)
                history += [Content(parts=[part], role="model")]


        response = await model.generate_content_async(
            contents=history,
            generation_config=generation_config,
            safety_settings=safety_settings,
        )

        # Kiểm tra và trả về kết quả từ phản hồi
        if len(response.candidates) > 0:
            if response.candidates[0].finish_reason == FinishReason.SAFETY:
                return """Sorry, I can't answer your question because it violates my privacy settings. Privacy settings are designed to protect users from harmful and inappropriate content. They include restrictions on topics that can be discussed, as well as specific keywords and phrases that are prohibited."""
            return response.candidates[0].text
        raise Exception("Something went wrong")


# Hàm TEST
# # Sample messages
# messages = [
#     ChatMessage(role=ChatMessageRole.USER, content="Hello, who is the president of the USA?"),
#     ChatMessage(role=ChatMessageRole.ASSISTANT, content="The president of the USA is Joe Biden."),
# ]

# # Instantiate the generator
# generator = VertexAIChatGenerator()

# print("Running the main function...")

# async def main():
#     try:
#         # Run the generator with the sample messages
#         result = await generator.run(messages=messages, system_prompt="Who is his wife", temperature=0.7)
#         print("Result:", result)
#     except Exception as e:
#         print(f"An error occurred: {e}")

# # Run the main function using asyncio
# asyncio.run(main())