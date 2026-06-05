from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import time
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI RFI Processor", version="1.0")

class RFIRequest(BaseModel):
    rfi_text: str
    trade_type: str = "general"

class RFIResponse(BaseModel):
    classification: str
    priority: str
    routed_to: str
    draft_response: str
    processing_time: float

@app.get("/")
def health_check():
    return {"status": "running", "service": "AI RFI Processor"}

@app.post("/process", response_model=RFIResponse)
def process_rfi_endpoint(request: RFIRequest):
    try:
        start = time.time()
        result = {
            "classification": "technical",
            "priority": "high",
            "routed_to": request.trade_type,
            "draft_response": f"RFI received: '{request.rfi_text[:60]}...' - Processing complete."
        }
        processing_time = time.time() - start
        return RFIResponse()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sample-rfis")
def get_sample_rfis():
    return {"rfis": ["Sample RFI 1", "Sample RFI 2", "Sample RFI 3"]}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
