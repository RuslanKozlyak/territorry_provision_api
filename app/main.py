from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager

from app.api.routers.effects import effects_controller
from app.api.utils.const import API_DESCRIPTION, API_TITLE

controllers = [effects_controller]

async def on_startup():
    ...

async def on_shutdown():
    ...

@asynccontextmanager
async def lifespan(router : FastAPI):
    await on_startup()
    yield
    await on_shutdown()

app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    lifespan=lifespan
)

# disable cors
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex='http://.*',
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=100)

@app.get("/", include_in_schema=False)
async def read_root():
    return RedirectResponse('/docs')

for controller in controllers:
    app.include_router(controller.router)