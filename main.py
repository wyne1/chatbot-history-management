# main.py

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from conversation_handler import handle_user_message
from chat_manager import ChatManager

app = FastAPI()

# Mount the static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# Initialize ChatManager
chat_manager = ChatManager()

class Message(BaseModel):
    user_id: str
    message_text: str

@app.post("/chat")
async def chat_endpoint(message: Message):
    response_text, token_count = handle_user_message(chat_manager, message.user_id, message.message_text)
    return {"response": response_text, "token_count": token_count}

@app.get("/redis_data/{user_id}")
async def get_redis_data(user_id: str):
    redis_data = chat_manager.get_redis_data(user_id)
    return JSONResponse(content=redis_data)

@app.get("/mongodb_data/{user_id}")
async def get_mongodb_data(user_id: str):
    mongodb_data = chat_manager.get_mongodb_data(user_id)
    return JSONResponse(content=mongodb_data)

@app.get("/", response_class=HTMLResponse)
async def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)