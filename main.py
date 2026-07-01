from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, generate_latest, REGISTRY
import time
import json
from collections import deque
import uuid
from datetime import datetime
import logging

app = FastAPI(title="Prometheus FastAPI Service")

# ====================== PROMETHEUS METRICS ======================
# Use a unique name to avoid conflicts with default metrics
REQUEST_COUNTER = Counter(
    'app_http_requests_total',           # Changed name to avoid duplication
    'Total HTTP requests', 
    ['method', 'path']
)

logs = deque(maxlen=1000)
start_time = time.time()

# ====================== LOGGING SETUP ======================
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

# ====================== MIDDLEWARE ======================
@app.middleware("http")
async def log_and_metrics_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    path = str(request.url.path)
    method = request.method
    
    logger.info(f"{method} {path}", extra={"path": path, "request_id": request_id})
    
    response = await call_next(request)
    
    REQUEST_COUNTER.labels(method=method, path=path).inc()
    
    return response

# ====================== ROUTES ======================
@app.get("/work")
async def work(n: int = 1):
    if n < 1:
        n = 1
    if n > 20:
        n = 20
    for _ in range(n):
        pass
    return {"email": "23f3003587@ds.study.iitm.ac.in", "done": n}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return PlainTextResponse(
        generate_latest(REGISTRY).decode('utf-8'),
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )

@app.get("/healthz")
async def healthz():
    return {"status": "ok", "uptime_s": round(time.time() - start_time, 2)}

@app.get("/logs/tail")
async def logs_tail(limit: int = 50):
    return list(logs)[-limit:]

@app.get("/")
async def root():
    return {"message": "Service running"}
