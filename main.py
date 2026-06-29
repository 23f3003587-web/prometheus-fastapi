from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, generate_latest
import time
import json
from collections import deque
import uuid
from datetime import datetime
import logging

app = FastAPI()

REQUEST_COUNTER = Counter('http_requests_total', 'Total HTTP requests', ['method', 'path'])

logs = deque(maxlen=1000)
start_time = time.time()

class JSONLogFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "level": record.levelname.lower(),
            "ts": datetime.utcnow().isoformat() + "Z",
            "path": getattr(record, "path", ""),
            "request_id": getattr(record, "request_id", str(uuid.uuid4()))
        })

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(JSONLogFormatter())
logger.addHandler(handler)

@app.middleware("http")
async def log_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    path = request.url.path
    
    response = await call_next(request)
    
    logger.info(f"Request {request.method} {path}", extra={
        "path": path,
        "request_id": request_id
    })
    
    REQUEST_COUNTER.labels(method=request.method, path=path).inc()
    return response

@app.get("/work")
async def work(n: int = 1):
    for _ in range(n):
        pass
    return {"email": "gangulysiddhartha22@gmail.com", "done": n}

@app.get("/metrics")
async def metrics():
    return PlainTextResponse(generate_latest().decode('utf-8'))

@app.get("/healthz")
async def healthz():
    return {
        "status": "ok",
        "uptime_s": round(time.time() - start_time, 2)
    }

@app.get("/logs/tail")
async def logs_tail(limit: int = 50):
    return list(logs)[-limit:]

# Capture logs to deque
def log_to_deque(record):
    try:
        log_entry = json.loads(record.getMessage())
        logs.append(log_entry)
    except:
        pass

logging.getLogger(__name__).addFilter(log_to_deque)
