from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, generate_latest, REGISTRY
import time
import json
from collections import deque
import uuid
from datetime import datetime
import logging
import os

app = FastAPI(title="Prometheus FastAPI Service")

# Prometheus Counter
REQUEST_COUNTER = Counter(
    'http_requests_total', 
    'Total HTTP requests', 
    ['method', 'path']
)

# In-memory log storage
logs = deque(maxlen=1000)
start_time = time.time()

# Structured JSON Logging
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
logger.propagate = False

# Log Capture Handler for /logs/tail
class LogCaptureHandler(logging.Handler):
    def emit(self, record):
        try:
            log_dict = json.loads(record.getMessage())
            logs.append(log_dict)
        except Exception:
            logs.append({
                "level": record.levelname.lower(),
                "ts": datetime.utcnow().isoformat() + "Z",
                "path": getattr(record, "path", ""),
                "request_id": getattr(record, "request_id", "")
            })

logger.addHandler(LogCaptureHandler())

# Middleware: Logging + Metrics
@app.middleware("http")
async def log_and_metrics_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    path = str(request.url.path)
    method = request.method

    # Log the request
    logger.info(f"{method} {path}", extra={
        "path": path,
        "request_id": request_id
    })

    # Process request
    response = await call_next(request)

    # Increment Prometheus counter
    REQUEST_COUNTER.labels(method=method, path=path).inc()

    return response

# Endpoints
@app.get("/work")
async def work(n: int = 1):
    # Simulate work
    for _ in range(n):
        pass
    return {"email": "gangulysiddhartha22@gmail.com", "done": n}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return PlainTextResponse(
        generate_latest(REGISTRY).decode('utf-8'),
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )

@app.get("/healthz")
async def healthz():
    return {
        "status": "ok",
        "uptime_s": round(time.time() - start_time, 2)
    }

@app.get("/logs/tail")
async def logs_tail(limit: int = 50):
    return list(logs)[-limit:]

@app.get("/")
async def root():
    return {"message": "Prometheus FastAPI Service is running"}
