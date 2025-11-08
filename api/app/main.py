from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.metrics import setup_metrics
from app.routers.flags import router as flags_router
from app.routers.health import router as health_router

app = FastAPI(title="Feature Flags Service", version="0.1.0")

# CORS (adjust as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health_router, prefix="")
app.include_router(flags_router, prefix="")

# Metrics endpoint
setup_metrics(app)
