"""
app/main.py
-----------
FastAPI application entry point.

This file:
1. Creates the FastAPI app instance
2. Registers all routers
3. Attaches middleware
4. Handles startup/shutdown lifecycle events
5. Serves Jinja2 HTML templates for frontend routes
6. Mounts static files
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.database import get_db
from app.middleware.logging_middleware import RequestLoggingMiddleware
from app.redis.redis_client import connect_redis, disconnect_redis
from app.routers import auth, chats, groups, users
from app.services.auth_service import login_user, register_user
from app.schemas.user import UserRegister
from app.utils.logger import get_logger, setup_logging
from app.websocket.ws_router import ws_router

setup_logging()
logger = get_logger(__name__)


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan handler.
    Code before `yield` runs on startup.
    Code after `yield` runs on shutdown.
    """
    logger.info("Starting ChatApp", version=settings.APP_VERSION)
    await connect_redis()
    yield
    logger.info("Shutting down ChatApp")
    await disconnect_redis()


# ── App Instance ──────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## Real-Time Chat Application API

Built with **FastAPI**, **PostgreSQL**, **Redis**, and **WebSockets**.

### Features
- JWT Authentication (access + refresh tokens)
- One-to-one private chat
- Group chat with admin roles
- Real-time messaging via WebSockets
- Online presence tracking via Redis
- Typing indicators

### Authentication
Click **Authorize** and enter: `Bearer <your_access_token>`
""",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware ─────────────────────────────────────────────────────────────────
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static Files ──────────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── Templates ─────────────────────────────────────────────────────────────────
templates = Jinja2Templates(directory="app/templates")

# ── API Routers ───────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(chats.router)
app.include_router(groups.router)
app.include_router(ws_router)


# ─────────────────────────────────────────────────────────────────────────────
# FRONTEND ROUTES (Jinja2 HTML pages)
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root(request: Request):
    """Redirect root to login."""
    return RedirectResponse(url="/login")


@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request, error: str = None):
    """Render the login page."""
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": error}
    )


@app.post("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle login form submission.
    On success: store token in cookie and redirect to dashboard.
    On failure: re-render login with error.
    """
    try:
        token_data = await login_user(email, password, db)
        response = RedirectResponse(url="/dashboard", status_code=302)
        # Store tokens in HTTP-only cookies for the browser frontend
        response.set_cookie(
            key="access_token",
            value=token_data.access_token,
            httponly=True,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            samesite="lax",
        )
        response.set_cookie(
            key="refresh_token",
            value=token_data.refresh_token,
            httponly=True,
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
            samesite="lax",
        )
        return response
    except HTTPException as e:
        # Show the exact error from the service layer (e.g. "Invalid email or password")
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": e.detail, "email": email},
            status_code=e.status_code,
        )
    except Exception:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Something went wrong. Please try again.", "email": email},
            status_code=500,
        )


@app.get("/register", response_class=HTMLResponse, include_in_schema=False)
async def register_page(request: Request):
    """Render the registration page."""
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register", response_class=HTMLResponse, include_in_schema=False)
async def register_submit(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Handle registration form submission."""
    # Client-side already checks, but server-side is authoritative
    if password != confirm_password:
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "error": "Passwords do not match",
                "username": username,
                "email": email,
            },
            status_code=400,
        )

    try:
        data = UserRegister(username=username, email=email, password=password)
        await register_user(data, db)
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "success": f"Account created successfully! Welcome, {username}. You can now log in.",
            },
        )
    except HTTPException as e:
        # HTTPException comes from register_user service (e.g. "Email already registered")
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "error": e.detail,
                "username": username,
                "email": email,
            },
            status_code=e.status_code,
        )
    except ValueError as e:
        # Pydantic validation errors (e.g. password too short, bad email format)
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "error": str(e),
                "username": username,
                "email": email,
            },
            status_code=400,
        )
    except Exception as e:
        logger.error("Unexpected registration error", error=str(e))
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "error": "Something went wrong. Please try again.",
                "username": username,
                "email": email,
            },
            status_code=500,
        )


@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_page(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Render the main chat dashboard.
    Requires a valid access_token cookie — redirects to login if missing.
    """
    access_token = request.cookies.get("access_token")

    if not access_token:
        return RedirectResponse(url="/login")

    # Decode token to get username for the navbar
    try:
        import uuid
        from app.auth.jwt_handler import decode_token
        from sqlalchemy import select
        from app.models.user import User

        user_id_str = decode_token(access_token, expected_type="access")
        result = await db.execute(select(User).where(User.id == uuid.UUID(user_id_str)))
        user = result.scalar_one_or_none()

        if not user:
            return RedirectResponse(url="/login")

        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "current_user": user.username,
                "current_user_id": str(user.id),
                "access_token": access_token,
            },
        )
    except Exception:
        return RedirectResponse(url="/login")


@app.get("/logout", include_in_schema=False)
async def logout():
    """Clear auth cookies and redirect to login."""
    response = RedirectResponse(url="/login")
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"], summary="Health check endpoint")
async def health_check():
    """
    Used by Docker healthcheck and load balancers to verify the app is running.
    Returns 200 OK if the app is healthy.
    """
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
