from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

router = APIRouter()


@router.get("/health")
async def health(request: Request) -> JSONResponse:
    try:
        async with request.app.state.db_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"

    status_code = 200 if db_status == "ok" else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "healthy", "db": db_status},
    )
