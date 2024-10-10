# main.py
import os
from fastapi import FastAPI, Request, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from conversation_handler import handle_user_message
from chat_manager import ChatManager
import logging
from test_runner import run_test

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI()

# Mount the static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# Initialize ChatManager
chat_manager = ChatManager()

class Message(BaseModel):
    user_id: str
    message_text: str

class ApproachChange(BaseModel):
    approach: str

@app.get("/test")
async def test_route():
    return {"message": "Test route is working"}

# @app.post("/run_test")
# async def run_test(file: UploadFile = File(...)):
#     # This is a placeholder. We'll implement the actual logic later.
#     return {"message": "Test completed"}

@app.post("/run_test")
async def run_test_endpoint(file: UploadFile = File(...)):
    logger.info(f"Received file: {file.filename}")
    try:
        contents = await file.read()
        temp_file_path = f"temp_{file.filename}"
        with open(temp_file_path, "wb") as f:
            f.write(contents)
        
        logger.info(f"Starting test run for file: {temp_file_path}")
        results = run_test(temp_file_path)
        logger.info("Test run completed successfully")
        
        os.remove(temp_file_path)  # Clean up the temporary file
        logger.info(f"Temporary file removed: {temp_file_path}")
        
        return JSONResponse(content=results)
    except Exception as e:
        logger.error(f"Error during test run: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/test_page")
async def test_page(request: Request):
    return templates.TemplateResponse("test_page.html", {"request": request})

@app.post("/chat")
async def chat_endpoint(message: Message):
    response_text, token_count = handle_user_message(chat_manager, message.user_id, message.message_text)
    return {"response": response_text, "token_count": token_count}

@app.post("/change_approach")
async def change_approach(approach_change: ApproachChange):
    chat_manager.set_approach(approach_change.approach)
    return {"status": "success", "new_approach": approach_change.approach}

@app.get("/internal_state/{user_id}")
async def get_internal_state(user_id: str):
    logger.info(f"Accessing internal state for user: {user_id}")
    try:
        internal_state = chat_manager.get_internal_state(user_id)
        logger.info(f"Internal state retrieved: {internal_state}")
        return JSONResponse(content=internal_state)
    except Exception as e:
        logger.error(f"Error retrieving internal state: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

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