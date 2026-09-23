from fastapi import FastAPI

app = FastAPI(title="NODOVIP Tabletop API")

@app.get("/health")
def health():
    return {"status": "ok"}
