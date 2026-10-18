FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml requirements.docker.lock.txt ./
COPY src ./src
RUN pip install --no-cache-dir -r requirements.docker.lock.txt && pip install --no-deps --no-build-isolation . && useradd --uid 10001 --create-home osint
USER 10001:10001
EXPOSE 8764
ENTRYPOINT ["osint-ner", "serve"]
CMD ["--host", "0.0.0.0", "--port", "8764", "--data", "/artifacts/inference.jsonl", "--run", "/artifacts/runs/baseline"]
