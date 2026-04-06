from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(
    title="ADS Dashboard API",
    description="Backend API for ADS Dashboard (SaaS Multi-tenant)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "ADS Dashboard API is running", "status": "online"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# API Routes
from app.api.v1 import api_router
app.include_router(api_router, prefix="/api/v1")
# For backward compatibility or simpler path
app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
