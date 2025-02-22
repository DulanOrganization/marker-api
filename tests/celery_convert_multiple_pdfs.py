import requests
import os
import time
# API Endpoints
CONVERT_API_URL = "http://localhost:9090/convert"
CELERY_API_URL = "http://localhost:9090/celery/convert"
MULTI_CONVERT_API_URL = "http://localhost:9090/batch_convert"


# PDF File Path
TEST_FILES_FOLDER = "test_files"



        
        
def celery_convert_multiple_pdfs(n_times=1,limit = 15):
    """Send all PDFs in the test_files folder to the /celery/convert endpoint N times."""
    pdf_files = [f for f in os.listdir(TEST_FILES_FOLDER) if f.endswith(".pdf")]
    counter= 0
    if not pdf_files:
        print("❌ No PDF files found in the test_files folder.")
        return

    for i in range(n_times):
        print(f"\n🚀 Cycle {i+1}/{n_times} - Sending {len(pdf_files)} PDF(s) to the API...")
        
        for pdf_file in pdf_files:
            counter +=1
            pdf_path = os.path.join(TEST_FILES_FOLDER, pdf_file)
            print(f"📤 Sending: {pdf_file}")
            time.sleep(5)
            if counter>limit:
                break
            try:
                with open(pdf_path, "rb") as file:
                    pdf_file_to_send = {"pdf_file": file}
                    response = requests.post(CELERY_API_URL, files=pdf_file_to_send)
                    
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Success: {pdf_file} - Response: {result}")
                else:
                    print(f"❌ Error for {pdf_file}: {response.status_code} - {response.text}")

            except Exception as e:
                print(f"⚠️ Failed to process {pdf_file}: {e}")
                
                
if __name__ == "__main__":

    
    
    # celery_convert_pdf()
        # Set the number of cycles (N) here
    celery_convert_multiple_pdfs(n_times=1)
    # celery_batch_convert(n_times=1,limit=3)
