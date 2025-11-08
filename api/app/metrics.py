from fastapi import FastAPI, Request
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
import time

REQUESTS = Counter("api_requests_total", "Total API requests", ["method", "endpoint", "http_status"])
LATENCY = Histogram("api_request_latency_seconds", "Request latency", ["method", "endpoint"])
EVALS = Counter("flag_evaluations_total", "Total flag evaluations", ["key", "result"])

def setup_metrics(app: FastAPI):

    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        elapsed = time.time() - start
        endpoint = request.url.path
        LATENCY.labels(request.method, endpoint).observe(elapsed)
        REQUESTS.labels(request.method, endpoint, response.status_code).inc()
        return response

    @app.get("/metrics")
    async def metrics():
        data = generate_latest()
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)
