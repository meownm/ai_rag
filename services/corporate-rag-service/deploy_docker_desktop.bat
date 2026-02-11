@echo off
docker build -t corporate-rag-service .
docker run -p 8100:8100 corporate-rag-service
