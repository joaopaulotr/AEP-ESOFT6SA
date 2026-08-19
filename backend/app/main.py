from fastapi import FastAPI

app = FastAPI(title="API - ESOFT6SA")

@app.get("/health")
def health():
    return {"status": "ok"}
