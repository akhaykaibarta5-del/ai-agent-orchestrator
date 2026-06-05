# day8_monitored_api.py
import os
import time
import json
from datetime import datetime
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import psutil

load_dotenv()

# ============ PROMETHEUS METRICS ============
REQUEST_COUNT = Counter('rfi_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('rfi_request_duration_seconds', 'Request duration', ['method', 'endpoint'])
TOKEN_COUNT = Counter('rfi_tokens_total', 'Total tokens used', ['model'])
COST_ESTIMATE = Counter('rfi_cost_usd_total', 'Estimated cost in USD', ['model'])
ACTIVE_REQUESTS = Gauge('rfi_active_requests', 'Currently active requests')
ERROR_COUNT = Counter('rfi_errors_total', 'Total errors', ['error_type'])

app = FastAPI(title="AI RFI Processor API - Monitored", version="2.0.0")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# CORS for dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ IN-MEMORY LOGS ============
request_logs = []
error_logs = []
daily_stats = {
    "date": datetime.now().strftime("%Y-%m-%d"),
    "total_requests": 0,
    "total_tokens": 0,
    "total_cost": 0.0,
    "avg_response_time": 0.0,
    "errors": 0
}

# ============ MODELS ============
class RFIRequest(BaseModel):
    rfi_text: str
    use_memory: bool = False

class RFIResponse(BaseModel):
    priority: str
    trade: str
    draft_response: str
    final_response: str
    status: str
    processing_time_ms: int
    tokens_used: int
    estimated_cost_usd: float
    timestamp: str

class StatsResponse(BaseModel):
    uptime_seconds: float
    total_requests: int
    total_tokens: int
    total_cost_usd: float
    avg_response_time_ms: float
    error_rate: float
    memory_usage_mb: float
    cpu_percent: float

# ============ MIDDLEWARE ============
@app.middleware("http")
async def monitoring_middleware(request: Request, call_next):
    start_time = time.time()
    ACTIVE_REQUESTS.inc()
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        return response
        
    except Exception as e:
        ERROR_COUNT.labels(error_type=type(e).__name__).inc()
        raise
        
    finally:
        ACTIVE_REQUESTS.dec()

# ============ ENDPOINTS ============
@app.get("/")
def health_check():
    return {
        "status": "alive",
        "service": "RFI Processor",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/process-rfi", response_model=RFIResponse)
def process_rfi(request: RFIRequest):
    start = time.time()
    
    # Estimate tokens (rough approximation)
    input_tokens = len(request.rfi_text.split()) * 1.3  # Approximate
    max_output_tokens = 1000
    
    # Classification + response
    prompt = f"""Classify and respond to this construction RFI:

RFI: {request.rfi_text}

Format:
PRIORITY: [urgent/normal/low]
TRADE: [structural/mep/architectural/general]
RESPONSE: [full technical response]"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=max_output_tokens
        )
        
        content = response.choices[0].message.content
        usage = response.usage
        
        # Track tokens and cost
        total_tokens = usage.total_tokens
        TOKEN_COUNT.labels(model="llama-3.3-70b").inc(total_tokens)
        
        # Cost: $0.59 per 1M tokens (Groq pricing)
        cost = (total_tokens / 1_000_000) * 0.59
        COST_ESTIMATE.labels(model="llama-3.3-70b").inc(cost)
        
        # Parse response
        priority = "normal"
        trade = "general"
        draft = content
        
        for line in content.split('\n'):
            if 'PRIORITY:' in line:
                priority = line.split(':')[1].strip().lower()
            elif 'TRADE:' in line:
                trade = line.split(':')[1].strip().lower()
            elif 'RESPONSE:' in line:
                draft = content[content.find('RESPONSE:'):].replace('RESPONSE:', '').strip()
        
        elapsed = int((time.time() - start) * 1000)
        
        # Log request
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "rfi_text": request.rfi_text[:100],
            "priority": priority,
            "trade": trade,
            "tokens": total_tokens,
            "cost_usd": round(cost, 6),
            "response_time_ms": elapsed,
            "status": "success"
        }
        request_logs.append(log_entry)
        
        # Update daily stats
        daily_stats["total_requests"] += 1
        daily_stats["total_tokens"] += total_tokens
        daily_stats["total_cost"] += cost
        daily_stats["avg_response_time"] = (
            (daily_stats["avg_response_time"] * (daily_stats["total_requests"] - 1) + elapsed)
            / daily_stats["total_requests"]
        )
        
        return RFIResponse(
            priority=priority,
            trade=trade,
            draft_response=draft[:500],
            final_response=draft,
            status="completed",
            processing_time_ms=elapsed,
            tokens_used=total_tokens,
            estimated_cost_usd=round(cost, 6),
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        ERROR_COUNT.labels(error_type=type(e).__name__).inc()
        daily_stats["errors"] += 1
        
        error_logs.append({
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "rfi_text": request.rfi_text[:100]
        })
        
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats", response_model=StatsResponse)
def get_stats():
    """Get current system statistics"""
    process = psutil.Process()
    
    return StatsResponse(
        uptime_seconds=time.time() - process.create_time(),
        total_requests=daily_stats["total_requests"],
        total_tokens=daily_stats["total_tokens"],
        total_cost_usd=round(daily_stats["total_cost"], 6),
        avg_response_time_ms=round(daily_stats["avg_response_time"], 2),
        error_rate=round(daily_stats["errors"] / max(daily_stats["total_requests"], 1), 4),
        memory_usage_mb=round(process.memory_info().rss / 1024 / 1024, 2),
        cpu_percent=psutil.cpu_percent(interval=1)
    )

@app.get("/logs")
def get_logs(limit: int = 50):
    """Get recent request logs"""
    return {
        "recent_requests": request_logs[-limit:],
        "recent_errors": error_logs[-10:],
        "total_logged": len(request_logs)
    }

@app.get("/dashboard")
def dashboard():
    """Simple HTML dashboard"""
    stats = get_stats()
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>RFI Processor Dashboard</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .card {{ background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .metric {{ display: inline-block; margin: 10px 20px; }}
            .metric-value {{ font-size: 32px; font-weight: bold; color: #2563eb; }}
            .metric-label {{ font-size: 14px; color: #666; }}
            .success {{ color: #16a34a; }}
            .warning {{ color: #ca8a04; }}
            .danger {{ color: #dc2626; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background: #f8fafc; font-weight: bold; }}
            .status {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; }}
            .status-success {{ background: #dcfce7; color: #166534; }}
            .status-error {{ background: #fee2e2; color: #991b1b; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 AI RFI Processor — Live Dashboard</h1>
            <p>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <div class="card">
                <h2>📊 Key Metrics</h2>
                <div class="metric">
                    <div class="metric-value { 'success' if stats.total_requests > 0 else '' }">{stats.total_requests}</div>
                    <div class="metric-label">Total Requests</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{stats.total_tokens:,}</div>
                    <div class="metric-label">Total Tokens</div>
                </div>
                <div class="metric">
                    <div class="metric-value ${stats.total_cost_usd:.4f}</div>
                    <div class="metric-label">Total Cost (USD)</div>
                </div>
                <div class="metric">
                    <div class="metric-value { 'warning' if stats.avg_response_time_ms > 5000 else 'success' }">{stats.avg_response_time_ms:.0f}ms</div>
                    <div class="metric-label">Avg Response Time</div>
                </div>
                <div class="metric">
                    <div class="metric-value { 'danger' if stats.error_rate > 0.05 else 'success' }">{stats.error_rate*100:.2f}%</div>
                    <div class="metric-label">Error Rate</div>
                </div>
            </div>
            
            <div class="card">
                <h2>🔧 System Health</h2>
                <div class="metric">
                    <div class="metric-value">{stats.uptime_seconds/3600:.1f}h</div>
                    <div class="metric-label">Uptime</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{stats.memory_usage_mb:.1f}MB</div>
                    <div class="metric-label">Memory Usage</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{stats.cpu_percent:.1f}%</div>
                    <div class="metric-label">CPU Usage</div>
                </div>
            </div>
            
            <div class="card">
                <h2>📝 Recent Requests</h2>
                <table>
                    <tr>
                        <th>Time</th>
                        <th>RFI (truncated)</th>
                        <th>Priority</th>
                        <th>Trade</th>
                        <th>Tokens</th>
                        <th>Cost</th>
                        <th>Time</th>
                        <th>Status</th>
                    </tr>
    """
    
    for log in request_logs[-20:]:
        status_class = "status-success" if log.get("status") == "success" else "status-error"
        html += f"""
                    <tr>
                        <td>{log.get('timestamp', 'N/A')[11:19]}</td>
                        <td>{log.get('rfi_text', 'N/A')[:50]}...</td>
                        <td>{log.get('priority', 'N/A')}</td>
                        <td>{log.get('trade', 'N/A')}</td>
                        <td>{log.get('tokens', 0):,}</td>
                        <td>${log.get('cost_usd', 0):.6f}</td>
                        <td>{log.get('response_time_ms', 0)}ms</td>
                        <td><span class="status {status_class}">{log.get('status', 'unknown')}</span></td>
                    </tr>
        """
    
    html += """
                </table>
            </div>
            
            <div class="card">
                <h2>🔗 API Endpoints</h2>
                <p><code>POST /process-rfi</code> — Process an RFI</p>
                <p><code>GET /stats</code> — System statistics</p>
                <p><code>GET /logs</code> — Recent request logs</p>
                <p><code>GET /metrics</code> — Prometheus metrics</p>
                <p><code>GET /dashboard</code> — This dashboard</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return Response(content=html, media_type="text/html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)