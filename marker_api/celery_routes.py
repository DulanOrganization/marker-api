from fastapi import HTTPException, UploadFile, File
from celery.result import AsyncResult
from fastapi.responses import JSONResponse
from marker_api.celery_tasks import convert_pdf_to_markdown, process_batch
import logging
import asyncio
import aiofiles
from typing import List

logger = logging.getLogger(__name__)


async def celery_convert_pdf(pdf_file: UploadFile = File(...)):
    contents = await pdf_file.read()
    task_id = convert_pdf_to_markdown.delay(pdf_file.filename, contents)
    return {"task_id": str(task_id), "status": "Processing"}


async def celery_result(task_id: str):
    task = AsyncResult(task_id)
    if not task.ready():
        return JSONResponse(
            status_code=202, content={"task_id": str(task_id), "status": "Processing"}
        )
    result = task.get()
    return {"task_id": task_id, "status": "Success", "result": result}


async def celery_offline_root():
    return {"message": "Celery is offline. No API is available."}


async def celery_convert_pdf_sync(pdf_file: UploadFile = File(...)):
    contents = await pdf_file.read()
    task = convert_pdf_to_markdown.delay(pdf_file.filename, contents)
    result = task.get(timeout=300)  # 5-minute timeout
    return {"status": "Success", "result": result}


async def celery_convert_pdf_concurrent_await(pdf_filename: str):
    try:
        # 1. Read PDF file
        try:
            async with aiofiles.open(pdf_filename, "rb") as pdf_file:
                contents = await pdf_file.read()
            logging.info(f"Successfully read PDF file. Size: {len(contents)} bytes")
            print(f"Successfully read PDF file. Size: {len(contents)} bytes")
        except Exception as e:
            logging.error(f"Error reading PDF file: {e}")
            print(f"Error reading PDF file: {e}")
            raise HTTPException(status_code=400, detail=f"Error reading PDF file: {str(e)}")

        # 2. Start Celery task
        try:
            task = convert_pdf_to_markdown.delay(pdf_filename, contents)
            logging.info(f"Celery task started: {task.id}")
            print(f"Celery task started: {task.id}")
        except Exception as e:
            logging.error(f"Failed to start Celery task: {e}")
            print(f"Failed to start Celery task: {e}")
            raise HTTPException(status_code=500, detail="Failed to start conversion task")

        # 3. Check task status with better handling
        async def check_task_status():
            attempts = 0
            max_attempts = 300  # 5 minutes with 1-second intervals
            
            while attempts < max_attempts:
                try:
                    # Get task status
                    task_status = AsyncResult(task.id)
                    
                    if task_status.ready():
                        if task_status.successful():
                            return task_status.get()
                        else:
                            error = task_status.result
                            logging.error(f"Task failed: {error}")
                            print(f"Task failed: {error}")
                            raise HTTPException(status_code=500, detail=f"Conversion failed: {str(error)}")
                    
                    # Log status periodically (every 30 seconds)
                    if attempts % 30 == 0:
                        logging.info(f"Task {task.id} status: {task_status.status}")
                        print(f"Task {task.id} status: {task_status.status}")
                    
                    attempts += 1
                    await asyncio.sleep(1)
                
                except Exception as e:
                    logging.error(f"Error checking task status: {e}")
                    print(f"Error checking task status: {e}")
                    raise HTTPException(status_code=500, detail=f"Error monitoring task: {str(e)}")
            
            raise asyncio.TimeoutError("Task exceeded maximum execution time")

        # 4. Wait for task completion with timeout
        try:
            result = await asyncio.wait_for(check_task_status(), timeout=300)
            
            logging.info("Task completed successfully")
            return {"status": "Success", "result": result}
            
        except asyncio.TimeoutError:
            logging.error("Task timed out after 300 seconds")
            print("Task timed out after 300 seconds")
            # Cancel the Celery task if possible
            task.revoke(terminate=True)
            logging.error(f"Task {task.id} timed out and was terminated")
            print(f"Task {task.id} timed out and was terminated")
            return JSONResponse(
                status_code=408,
                content={
                    "status": "Timeout",
                    "message": "Task processing took too long",
                    "task_id": task.id
                }
            )
            
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        print(f"Unexpected error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "Error",
                "message": f"An unexpected error occurred: {str(e)}"
            }
        )


# async def celery_batch_convert(pdf_files: List[UploadFile] = File(...)):
#     batch_data = []
#     for pdf_file in pdf_files:
#         contents = await pdf_file.read()
#         batch_data.append((pdf_file.filename, contents))

#     # Start a single task to process the entire batch
#     task = process_batch.delay(batch_data)

#     return {
#         "task_id": str(task.id),
#         "status": "Processing",
#     }


# async def celery_batch_result(task_id: str):
#     task = AsyncResult(task_id)

#     if not task.ready():
#         return JSONResponse(
#             status_code=202,
#             content={
#                 "task_id": str(task_id),
#                 "status": "Processing",
#             },
#         )

#     try:
#         results = task.get()
#         return JSONResponse(
#             status_code=200,
#             content={"task_id": task_id, "status": "Success", "results": results},
#         )
#     except Exception as e:
#         logger.error(f"Error retrieving results for task {task_id}: {str(e)}")
#         return JSONResponse(
#             status_code=500,
#             content={
#                 "task_id": task_id,
#                 "status": "Error",
#                 "message": "An error occurred while retrieving the results",
#             },
#         )


async def celery_batch_convert(pdf_files: List[UploadFile] = File(...)):
    batch_data = []
    for pdf_file in pdf_files:
        contents = await pdf_file.read()
        batch_data.append((pdf_file.filename, contents))

    # Start a single task to process the entire batch
    task = process_batch.delay(batch_data)

    return {"task_id": str(task.id), "status": "Processing", "total": len(batch_data)}


async def celery_batch_result(task_id: str):
    task = AsyncResult(task_id)

    if not task.ready():
        # Check if we can access task information
        if task.info and isinstance(task.info, dict) and "current" in task.info:
            current = task.info["current"]
            total = task.info["total"]
            return JSONResponse(
                status_code=202,
                content={
                    "task_id": str(task_id),
                    "status": "Processing",
                    "progress": f"{current}/{total}",
                    "percent": round((current / total) * 100, 2),
                },
            )
        else:
            return JSONResponse(
                status_code=202,
                content={
                    "task_id": str(task_id),
                    "status": "Processing",
                },
            )

    try:
        results = task.get()
        return JSONResponse(
            status_code=200,
            content={
                "task_id": task_id,
                "status": "Success",
                "results": results,
                "total": len(results),
                "successful": sum(1 for r in results if r.get("status") == "Success"),
                "failed": sum(1 for r in results if r.get("status") == "Error"),
            },
        )
    except Exception as e:
        logger.error(f"Error retrieving results for task {task_id}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "task_id": task_id,
                "status": "Error",
                "message": "An error occurred while retrieving the results",
            },
        )
