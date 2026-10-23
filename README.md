# Automotive Cybersecurity TARA Assistant

Case Study 3 from the Tata TechPulse "Automotive Engineering AI" reference document. Assists a
cybersecurity engineer with asset identification, threat scenario generation, risk assessment, and
mitigation recommendation for a connected-vehicle system, using synthetic (fake) data.

## Tech stack

- **Backend + AI:** Python, FastAPI
- **Frontend:** Streamlit
- **Vector database:** FAISS (local, in-memory)
- **Embeddings:** sentence-transformers (`all-MiniLM-L6-v2`)
- **LLM:** local model served by [Ollama](https://ollama.com) (default: `qwen3:4b`, override with env var `TARA_LLM_MODEL`)
- **Structured storage:** SQLite via SQLAlchemy

## How it works

1. On startup, the backend reads the synthetic architecture document, threat library, and
   mitigation library, chunks/embeds them, and stores them in three FAISS collections.
2. The engineer extracts assets from the architecture doc (LLM-based extraction).
3. For a selected asset, the app retrieves the closest matching known threats (RAG) and asks the
   LLM which ones apply and why.
4. The engineer rates Impact and Feasibility; a deterministic rule (not AI) computes the risk level.
5. The app retrieves matching mitigations (RAG) and drafts a recommendation; the engineer must
   approve it before it's considered final.
6. A traceability report ties Asset -> Threat -> Risk -> Mitigation together.

Every AI-generated item carries a citation back to its source, and nothing becomes "Approved"
without a human clicking Approve - both are guardrails required by the case study document.

## Setup

1. Create and activate a virtual environment, then install dependencies:
   ```
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Install [Ollama](https://ollama.com) and pull a model (skip if you already have `qwen3:4b`
   pulled - check with `ollama list`):
   ```
   ollama pull qwen3:4b
   ```

3. Create the database tables (optional - the backend also does this automatically on startup):
   ```
   python -m app.create_tables
   ```

4. Run the backend:
   ```
   uvicorn app.main:app --reload --port 8000
   ```

5. In a second terminal (with venv activated), run the frontend:
   ```
   streamlit run streamlit_app.py
   ```

6. Open the Streamlit page and walk through the tabs in order: Assets -> Threats -> Risk
   Assessment -> Mitigations -> Traceability Report.

## Project structure

```
app/
├── main.py                  - FastAPI app, wires up routers, loads knowledge base on startup
├── create_tables.py         - one-off script to create the SQLite tables
├── schemas.py                - Pydantic request models
├── data/                      - synthetic architecture doc, threat library, mitigation library
├── models/
│   ├── database.py           - DB connection/session setup
│   └── models.py              - the 6 SQLAlchemy table classes
├── services/
│   ├── embedding_service.py  - turns text into vectors
│   ├── vector_store.py        - FAISS wrapper (add/search)
│   ├── chunker.py              - splits text into chunks
│   ├── llm_service.py          - calls the local LLM, parses JSON out of its reply
│   ├── ai_tasks.py              - builds the actual prompts for each AI step
│   ├── risk_scoring.py          - deterministic risk matrix (no AI)
│   ├── audit.py                  - writes to the audit log table
│   └── knowledge_base.py         - loads synthetic data into the vector stores at startup
└── routers/
    ├── assets.py, threats.py, risk.py, mitigations.py, report.py
streamlit_app.py             - the frontend
evaluation/                  - ground truth, evaluation script, end-to-end demo, saved results
scripts/capture_screenshots.py - drives the UI to capture evidence screenshots
```

## Evaluation

```
python -m evaluation.run_evaluation --llm    # full run, needs Ollama (~2 min); drop --llm for retrieval-only (~20 s)
python -m evaluation.e2e_demo                # runs the whole workflow through the API (backend must be running)
```

Ground truth: `evaluation/ground_truth.json`. Results (metrics, sample outputs with citations, end-to-end log,
UI screenshots): `evaluation/results/`. `python -m scripts.capture_screenshots` re-captures the UI screenshots
(backend, Streamlit and Ollama must be running, with an empty `tara.db`).

## Deployment (Streamlit Community Cloud)

Deployed from this repo with `streamlit_app.py` as the entry point. On a hosted run the Streamlit process starts the
FastAPI backend in a background thread. When the secret `GROQ_API_KEY` is set, LLM calls go to Groq
(`llama-3.3-70b-versatile`) instead of a local Ollama model; without it the app uses Ollama as described above.
