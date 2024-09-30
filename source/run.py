from config.env_config import PORT_NUMBER
from schemas.api_response_schema import make_response
from source.routers import chatbot_router
import uvicorn
import logging
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware


# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(debug=True)
# AI_CHATBOT_URL = os.getenv("AI_CHATBOT_URL", "http://127.0.0.1:6379")
# top_k = 11

# # Thêm SessionMiddleware để quản lý session
# app.add_middleware(SessionMiddleware, secret_key="supersecretkey")

# Add CORS middleware
origins = [
    "http://localhost",
    f"http://localhost:{PORT_NUMBER}",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Custom Exception Handler for Input Data Validation
async def custom_exception_handler(request: Request, exc: RequestValidationError):
    response = make_response(-501, content="Error in Input Data Validation.", summary_history="")
    response = response.dict()
    return JSONResponse(response, status_code=400)

# Chatbot endpoints
chatbot_endpoints = ""
app.include_router(chatbot_router.chat_router, prefix=chatbot_endpoints[:-1])
app.add_exception_handler(RequestValidationError, custom_exception_handler)

if __name__ == "__main__":
    uvicorn.run("run:app", host="0.0.0.0", port=7000, reload=False)