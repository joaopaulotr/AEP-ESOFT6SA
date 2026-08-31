from fastapi import FastAPI
from app.api.v1.endpoints import session, turns


app = FastAPI(title="API - ESOFT6SA")
app.include_router(session.router)
app.include_router(turns.router)

@app.get("/health")
def health():
    return {"status": "ok"}


