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
        
        # Simulate processing logic
        classification = "technical"
        priority = "high"
        routed_to = request.trade_type
        draft_response = f"RFI received: '{request.rfi_text[:60]}...' - Processing complete. This will be automated with full LangGraph pipeline."
        
        processing_time = time.time() - start
        
        return RFIResponse(
            classification=classification,
            priority=priority,
            routed_to=routed_to,
            draft_response=draft_response,
            processing_time=round(processing_time, 2)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sample-rfis")
def get_sample_rfis():
    return {
        "rfis": [
            "What is the required concrete strength for the foundation footing?",
            "The electrical panel location conflicts with the HVAC ductwork.",
            "The window specification calls for low-E glass but supplier delivered standard glass."
        ]
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)