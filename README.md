# Marker API

1. git clone https://github.com/DulanOrganization/marker-api
2. cd marker-api
3. conda create -n marker-api python=3.11
4. conda activate marker-api
5. pip install poetry
6. poetry install


# For running in production

## Docker Setup
1. sudo apt-get update && sudo apt-get install -y apt-utils
2. docker build -f docker/Dockerfile.gpu.server -t marker-api-gpu .

## Docker Compose Setup
1. docker compose -f docker-compose.gpu.yml up --build --scale celery_worker=3

Sample curl command to test the API

```
curl --location 'http://0.0.0.0:8010/convert' \
--form 'pdf_file=@"/Users/manojpreveenvelusamy/Documents/Finden/Data/POC Docs/491428.pdf"'
```

