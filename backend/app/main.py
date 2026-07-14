from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import chat, hcps, interactions

Base.metadata.create_all(bind=engine)

app = FastAPI(title="HCP CRM API")

# Vite's default dev server port. Add your deployed frontend origin here too.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(interactions.router)
app.include_router(chat.router)
app.include_router(hcps.router)


@app.get("/health")
def health():
    return {"status": "ok"}
