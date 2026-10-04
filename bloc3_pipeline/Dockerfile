FROM python:3.12-slim
WORKDIR /app
COPY pipeline /app/pipeline
USER 65532:65532
ENTRYPOINT ["python", "-m", "pipeline"]
CMD ["schedule", "--config", "/config/corpus.json", "--cycles", "0"]
