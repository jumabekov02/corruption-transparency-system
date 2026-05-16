from fastapi import FastAPI

app = FastAPI(title="Corruption Monitoring API")

@app.get("/health")
def health():
    return {"status": "ok"}

