import argparse
import logging
import asyncio
from fastapi import FastAPI, UploadFile, File, Body
from celery.exceptions import TimeoutError
from fastapi.middleware.cors import CORSMiddleware
from marker_api.celery_worker import celery_app
from marker_api.utils import print_markerapi_text_art
from marker.logger import configure_logging
from marker_api.celery_routes import (
    celery_convert_pdf,
    celery_result,
    celery_convert_pdf_concurrent_await,
    celery_batch_convert,
    celery_batch_result,
)
import gradio as gr
from marker_api.demo import demo_ui
from marker_api.model.schema import (
    BatchConversionResponse,
    BatchResultResponse,
    CeleryResultResponse,
    CeleryTaskResponse,
    ConversionResponse,
    HealthResponse,
    ServerType,
)
from typing import List
from contextlib import asynccontextmanager

# Initialize logging
configure_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print_markerapi_text_art()
    await setup_celery()
    yield
    # Shutdown
    pass

app = FastAPI(lifespan=lifespan)

logger.info("Configuring CORS middleware")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

@app.get("/health", response_model=HealthResponse)
def server():
    """
    Root endpoint to check server status.

    Returns:
    HealthResponse: A welcome message, server type, and number of workers (if distributed).
    """
    worker_count = len(celery_app.control.inspect().stats() or {})
    server_type = ServerType.distributed if worker_count > 0 else ServerType.simple
    return HealthResponse(
        message="Welcome to Marker-api",
        type=server_type,
        workers=worker_count if server_type == ServerType.distributed else None,
    )


def is_celery_alive() -> bool:
    logger.debug("Checking if Celery is alive")
    try:
        result = celery_app.send_task("my_custom_ping")
        result.get(timeout=90)
        logger.info("Celery is alive")
        return True
    except (TimeoutError, Exception) as e:
        logger.warning(f"Celery is not responding: {str(e)}")
        return False


def setup_routes(app: FastAPI, celery_live: bool):
    logger.info("Setting up routes")
    if celery_live:
        logger.info("Adding Celery routes")
        
        @app.post("/convert", response_model=ConversionResponse)
        async def convert_pdf(pdf_filename: str = Body(..., embed=True)):
            print("pdf_filename : ", pdf_filename, flush=True)
            return await celery_convert_pdf_concurrent_await(pdf_filename)

        @app.post("/celery/convert", response_model=CeleryTaskResponse)
        async def celery_convert(pdf_file: UploadFile = File(...)):
            return await celery_convert_pdf(pdf_file)

        @app.get("/celery/result/{task_id}", response_model=CeleryResultResponse)
        async def get_celery_result(task_id: str):
            return await celery_result(task_id)

        @app.post("/batch_convert", response_model=BatchConversionResponse)
        async def batch_convert(pdf_files: List[UploadFile] = File(...)):
            return await celery_batch_convert(pdf_files)

        @app.get("/batch_convert/result/{task_id}", response_model=BatchResultResponse)
        async def get_batch_result(task_id: str):
            return await celery_batch_result(task_id)

        logger.info("Adding real-time conversion route")
    else:
        logger.warning("Celery routes not added as Celery is not alive")
    app = gr.mount_gradio_app(app, demo_ui, path="/demo")


def parse_args():
    logger.debug("Parsing command line arguments")
    parser = argparse.ArgumentParser(description="Run FastAPI with Uvicorn.")
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Host to run the FastAPI app"
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="Port to run the FastAPI app"
    )
    return parser.parse_args()

async def setup_celery():
    await asyncio.sleep(90)
    result = celery_app.send_task("test_hello")
    print("Got result:", result.get(timeout=90))
    celery_alive = is_celery_alive()
    print("Celery alive:", celery_alive)
    setup_routes(app, celery_alive)


