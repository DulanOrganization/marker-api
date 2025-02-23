from celery import Task
from marker_api.celery_worker import celery_app
from marker.convert import convert_single_pdf
from marker.models import load_all_models
import io
import logging
from marker_api.utils import process_image_to_base64
from celery.signals import worker_process_init

logger = logging.getLogger(__name__)

model_list = None


@worker_process_init.connect
def initialize_models(**kwargs):
    global model_list
    if not model_list:
        model_list = load_all_models()
        print("Models loaded at worker startup")

# MODEL_CACHE = None

# def get_model():
#     global MODEL_CACHE
#     if MODEL_CACHE is None:
#         # Load model(s) here, including any GPU .to(device) calls
#         MODEL_CACHE = load_all_models()
#     return MODEL_CACHE


class PDFConversionTask(Task):
    abstract = True

    def __init__(self):
        super().__init__()

    def __call__(self, *args, **kwargs):
        # Use the global model_list initialized at worker startup
        return self.run(*args, **kwargs)


# 1️⃣ Task: Convert PDF to Markdown and Send to Queue
@celery_app.task(ignore_result=False, bind=True, base=PDFConversionTask, name="convert_pdf")
def convert_pdf_to_markdown(self, filename, pdf_content):
    """Converts PDF to Markdown and sends result to process_continue_queue."""
    try:
        print(f"📄 Processing {filename}...")

        # Convert PDF
        pdf_file = io.BytesIO(pdf_content)
        markdown_text, images, metadata = convert_single_pdf(pdf_file, model_list)
        print(f"✅ PDF Conversion completed for {filename}")

        # Process images to Base64
        image_data = {
            img_filename: process_image_to_base64(image, img_filename)
            for img_filename, image in images.items()
        }

        # Prepare result
        result = {
            "filename": filename,
            "markdown": markdown_text,
            "metadata": metadata,
            "images": image_data,
            "status": "ok",
        }

        # Send results to process_continue_queue
        send_to_process_continue_queue.delay(filename, markdown_text, metadata)

        return result

    except Exception as e:
        logger.error(f"❌ Error processing {filename}: {str(e)}")
        raise e


# 2️⃣ Task: Send results to process_continue_queue
@celery_app.task(queue="process_continue_queue", name="send_to_process_continue_queue")
def send_to_process_continue_queue(filename, markdown, metadata):
    """Sends the processed PDF result to the next queue for embedding."""
    try:
        task_payload = {
            "filename": filename,
            "markdown": markdown,
            "metadata": metadata
        }

        print(f"📤 Sending {filename} to process_continue_queue...")

        # Send task to Godseye for further processing
        celery_app.send_task("godseye.tasks.process_continue_task", args=[task_payload])

        print(f"✅ Task sent for {filename}.")
        return {"status": "success", "filename": filename}

    except Exception as e:
        logger.error(f"❌ Failed to send {filename} to queue: {str(e)}")
        raise e
# @celery_app.task(
#     ignore_result=False, bind=True, base=PDFConversionTask, name="process_batch"
# )
# def process_batch(self, batch_data):
#     results = []
#     for filename, pdf_content in batch_data:
#         try:
#             result = convert_pdf_to_markdown(filename, pdf_content)
#             results.append(result)
#         except Exception as e:
#             logger.error(f"Error processing {filename}: {str(e)}")
#             results.append({"filename": filename, "status": "Error", "error": str(e)})
#     return results


@celery_app.task(
    ignore_result=False, bind=True, base=PDFConversionTask, name="process_batch"
)
def process_batch(self, batch_data):
    results = []
    total = len(batch_data)
    for i, (filename, pdf_content) in enumerate(batch_data, start=1):
        try:
            result = convert_pdf_to_markdown(filename, pdf_content)
            results.append(result)
        except Exception as e:
            logger.error(f"Error processing {filename}: {str(e)}")
            results.append({"filename": filename, "status": "Error", "error": str(e)})

        # Update progress
        self.update_state(state="PROGRESS", meta={"current": i, "total": total})

    return results

@celery_app.task(ignore_result=False, bind=True, base=PDFConversionTask, name="my_custom_ping")
def ping(self):
    print("Ping task received!")  # or use a logger
    return "pong"

@celery_app.task(ignore_result=False, bind=True, base=PDFConversionTask, name="test_hello")
def test_hello(self):
    print("test_hello ran")
    return "hello"