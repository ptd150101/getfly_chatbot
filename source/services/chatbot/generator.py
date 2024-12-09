import asyncio
from typing import Optional
from langfuse.decorators import observe
import vertexai
from vertexai.generative_models import GenerativeModel, FinishReason
import vertexai.generative_models as generative_models
from google.oauth2.service_account import Credentials


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


# Class Generator cơ bản
class Generator:
    async def run(
        self,
        prompt: str,
        temperature: Optional[float] = None,
    ) -> str:
        pass



class VertexAIGenerator(Generator):
    def __init__(
        self,
        model: str,
        credentials: str,
        project_id: str = "communi-ai",
        location: str = "asia-southeast1",
    ) -> None:
        
        vertexai.init(project=project_id, location=location, credentials=credentials)
        self.model = GenerativeModel(
            model_name=model
        )

    @observe(name="VertexAIGenerator", as_type="generation")
    async def run(
        self,
        prompt: str,
        temperature: Optional[float] = None
    ) -> str:
        

        response = await self.model.generate_content_async(
            [prompt],
            generation_config=generation_config,
            safety_settings=safety_settings,
        )

        # Kiểm tra và trả về kết quả từ phản hồi
        if len(response.candidates) > 0:
            if response.candidates[0].finish_reason == FinishReason.SAFETY:
                return """Sorry, I can't answer your question because it violates my privacy settings. Privacy settings are designed to protect users from harmful and inappropriate content. They include restrictions on topics that can be discussed, as well as specific keywords and phrases that are prohibited."""
            return response.text
        raise Exception("Something went wrong")


# Hàm test
# async def main():
#     # Tạo một instance của VertexAIGenerator
#     generator = VertexAIGenerator()

#     # Gọi hàm run với một prompt và temperature tùy chọn
#     prompt = "who is president of USA"
#     result = await generator.run(prompt, temperature=0.7)

#     # In kết quả
#     print(result)


# # Chạy chương trình
# asyncio.run(main())
