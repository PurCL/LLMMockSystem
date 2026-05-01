"""Wrapper that imports the Bambuddy app and adds a simple protected endpoint.

Uses FastAPI middleware instead of a route, since the app's router structure
prevents adding routes directly.
"""

from backend.app.main import app  # noqa: F401 — re-export for uvicorn
from starlette.requests import Request
from starlette.responses import JSONResponse
import jwt

SECRET_FLAG = "SECRET_FLAG_CVE202625505"
JWT_SECRET = "bambuddy-secret-key-change-in-production"
ALGORITHM = "HS256"


@app.middleware("http")
async def flag_endpoint(request: Request, call_next):
    if request.url.path == "/api/v1/flag":
        # Require valid JWT
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Not authenticated"},
            )
        token = auth_header.split(" ", 1)[1]
        try:
            jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        except jwt.InvalidTokenError:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid token"},
            )
        return JSONResponse(content={"flag": SECRET_FLAG})
    return await call_next(request)
