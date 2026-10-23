FROM python:3.11-slim
RUN useradd -m -u 1000 user
WORKDIR /home/user/app
COPY requirements.txt .
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu torch && \
    pip install --no-cache-dir -r requirements.txt
COPY --chown=user . .
USER user
ENV HOME=/home/user HF_HOME=/home/user/.cache
# bake the embedding model into the image so startup is fast
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --port 8000 & streamlit run streamlit_app.py --server.port 7860 --server.address 0.0.0.0 --server.headless true"]
