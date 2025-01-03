import asyncio
from typing import Optional
from langfuse.decorators import observe
import vertexai
from vertexai.generative_models import GenerativeModel
import vertexai.generative_models as generative_models
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
            model_name=model,
            generation_config=generation_config,
            safety_settings=safety_settings
        )

    @observe(name="VertexAIGenerator", as_type="generation")
    async def run(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        response_model: Optional[str] = None,
    ) -> str:
        client = instructor.from_vertexai(
            client=self.model,
            mode=instructor.Mode.VERTEXAI_TOOLS,
            _async=True,
        )
        prompt = [
            {
                "role": "user",
                "content": prompt
            }
        ]
        response = await client.create(
            messages=prompt,
            response_model=response_model,
            max_retries=20,
            # stream=True,
        )
        return response
        
