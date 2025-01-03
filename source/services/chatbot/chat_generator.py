import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from langfuse.decorators import observe
from schemas.api_response_schema import ChatMessage, ChatMessageRole
from typing import Optional, List
import vertexai
from vertexai.generative_models import GenerativeModel, Part, Content, FinishReason
import vertexai.preview.generative_models as generative_models
import instructor



# ID dự án Google Cloud
my_project = "communi-ai"

# Cấu hình tạo nội dung
generation_config = {
    "max_output_tokens": 8192,
    "temperature": 0.2,
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
        response_model: Optional[str] = None,
    ) -> str:
        
        model = GenerativeModel(
            model_name=self.model_name,
            generation_config=generation_config,
            safety_settings=safety_settings,
            system_instruction=system_prompt,
        )

        client = instructor.from_vertexai(
            client=model,
            mode=instructor.Mode.VERTEXAI_TOOLS,
            _async=True,            
        )

        history: List[Content] = []
        for message in messages[1:]:
            if message.role == ChatMessageRole.USER:
                part = Part.from_text(message.content)  
                history += [Content(parts=[part], role="user")]
            elif message.role == ChatMessageRole.ASSISTANT:
                part = Part.from_text(message.content)
                history += [Content(parts=[part], role="assistant")]

        response = await client.create(
            messages=history,
            response_model=response_model,
            max_retries=20,
            # stream=True,
        )
        
        return response
        # # Chờ để nhận kết quả từ async_generator
        # async for result in response:
        #     if len(result.candidates) > 0:
        #         if result.candidates[0].finish_reason == FinishReason.SAFETY:
        #             return """Sorry, I can't answer your question because it violates my privacy settings. Privacy settings are designed to protect users from harmful and inappropriate content. They include restrictions on topics that can be discussed, as well as specific keywords and phrases that are prohibited."""
        #         return result.text
        
        # raise Exception("Something went wrong")
