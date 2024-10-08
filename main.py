# main.py

from config import OPENAI_API_KEY  # Ensure config is imported first
from pydantic import BaseModel
from conversation_handler import handle_user_message
from chat_manager import ChatManager

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


# ... other imports ...

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development only. Specify domains in production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Serve the frontend
@app.get("/", response_class=HTMLResponse)
async def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# Initialize ChatManager
chat_manager = ChatManager()

class Message(BaseModel):
    user_id: str
    message_text: str

@app.post("/chat")
async def chat_endpoint(message: Message):
    response_text, token_count = handle_user_message(chat_manager, message.user_id, message.message_text)
    return {"response": response_text, "token_count": token_count}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)