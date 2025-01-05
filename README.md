# Marker API

1. git clone https://github.com/DulanOrganization/marker-api


# For running in production

## Docker Setup
1. sudo apt-get update && sudo apt-get install -y apt-utils
2. docker build -f docker/Dockerfile.gpu.distributed-server -t marker-api-gpu .

## Docker Compose Setup
1. docker compose -f docker-compose.gpu.yml up --build --scale celery_worker=3 --scale sentence_text_embedding=1 --scale image_embedding=1 --scale tika=1

### INFORMATION : (Services : Ports)

1. Marker API : 8010
2. Sentence Text Embedding API : 8020
3. Image Embedding API : 8030
4. Tika Server : 9998

Sample curl command to test the Marker API
```
curl --location 'http://0.0.0.0:8010/convert' \
--form 'pdf_file=@"/Users/manojpreveenvelusamy/Documents/Finden/Data/POC Docs/491428.pdf"'
```

Sample curl command to test the Sentence Text Embedding API
```
curl --location 'http://0.0.0.0:8020/get_embeddings' \
--header 'Content-Type: application/json' \
--data '{"texts": ["Hello, world!", "This is a test sentence."]}'
```

Sample curl command to test the Image Embedding API
```
curl --location 'http://0.0.0.0:8030/get_embeddings' \
--header 'Content-Type: application/json' \
--data '{"texts": ["Hello, world!", "This is a test sentence."], "images": ["data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAf/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwD/2Q=="]}'
```