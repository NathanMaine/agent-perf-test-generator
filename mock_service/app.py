from fastapi import FastAPI

app = FastAPI(title="Mock Service")


@app.get("/api/demo")
async def demo():
    return {"message": "ok"}


# Run with: uvicorn mock_service.app:app --port 8001 --reload
