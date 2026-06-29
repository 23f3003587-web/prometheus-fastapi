from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, generate_latest
import time
import json
import logging
from datetime import datetime
from collections import deque
import uuid

app = FastAPI()

# Prometheus Counter
REQUEST_COUNTER = Counter('http_requests_total', 'Total HTTP requests', ['method', 'path'])

# In-memory logs (last 1000 entries)
logs = deque(maxlen=1000)
start_time = time.time()

# Structured JSON Logging
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "level": record.levelname.lower(),
            "ts": datetime.utcnow().isoformat() + "Z",
            "path": getattr(record, "path", ""),
            "request_id": getattr(record, "request_id", ""),
            "message": record.getMessage()
        }
        return json.dumps(log_entry)

logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start = time.time()
    
    # Attach to request state for logging
    request.state.request_id = request_id
    
    response = await call_next(request)
    
    duration = time.time() - start
    logger.info(f"{request.method} {request.url.path}", 
                extra={"path": request.url.path, "request_id": request_id})
    
    REQUEST_COUNTER.labels(method=request.method, path=request.url.path).inc()
    return response

@app.get("/work")
async def work(n: int = 1, request: Request = None):
    # Simulate work
    for _ in range(n):
        pass
    return {
        "email": "gangulysiddhartha22@gmail.com",
        "done": n
    }

@app.get("/metrics")
async def metrics():
    return PlainTextResponse(generate_latest())

@app.get("/healthz")
async def healthz():
    uptime = time.time() - start_time
    return {
        "status": "ok",
        "uptime_s": round(uptime, 2)
    }

@app.get("/logs/tail")
async def logs_tail(limit: int = 50):
    limit = min(limit, 1000)
    return list(logs) if logs else []

# Capture logs into deque
def capture_log(record):
    if isinstance(record.msg, str):
        entry = json.loads(record.msg) if record.msg.startswith('{') else {
            "level": record.levelname.lower(),
            "ts": datetime.utcnow().isoformat() + "Z",
            "path": getattr(record, "path", ""),
            "request_id": getattr(record, "request_id", "")
        }
        logs.append(entry)

logging.getLogger("app").addFilter(capture_log)  # Simplified capture
