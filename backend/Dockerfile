FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .

# torch comes in via sentence-transformers. The default index pulls the CUDA
# build (~5 GB of nvidia-* wheels) onto a server with no GPU, so take the
# CPU-only wheel first and let the rest of requirements.txt resolve against it.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
