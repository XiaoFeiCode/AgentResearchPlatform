"""Entry point — runs FastAPI app from app/ package."""
from app.main import app

if __name__ == "__main__":
    import uvicorn
    from app.config import settings

    host = settings.HOST
    port = settings.PORT

    uvicorn.run(app, host=host, port=port, log_level="debug")
