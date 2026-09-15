from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .routers import projects, repositories, changes, analysis, workflow

app = FastAPI(title="Smorx API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(repositories.router)
app.include_router(changes.router)
app.include_router(analysis.router)
app.include_router(workflow.router)

@app.get("/health")
async def health():
    return {"status": "ok"}
