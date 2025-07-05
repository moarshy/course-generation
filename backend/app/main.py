from fastapi import FastAPI

app = FastAPI(title="Naptha Course Creator Backend", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Welcome to Naptha Course Creator Backend"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"} 