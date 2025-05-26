from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import pantry, recipe, session

# from routes import sessions, pantry
from api.settings import Settings

import uvicorn

settings = Settings()

app = FastAPI(
    title="PantryChef API",
    description="API for recommending recipes based on pantry ingredients",
    version="0.1.0",
    openapi_url="/openapi.json" if settings.DEBUG else None,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(recipe.router, prefix="/api/recipes", tags=["recipes"])
app.include_router(session.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(pantry.router, prefix="/api/pantry", tags=["pantry"])
# app.include_router(ai.router, prefix="/api/ai", tags=["ai"])


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Welcome to PantryChef API", "docs": "/docs", "redoc": "/redoc"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
