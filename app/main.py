from fastapi import FastAPI
from app.models.database import Base, engine
from app.models import models  # noqa: F401 - needed so tables get registered
from app.services.knowledge_base import load_knowledge_base
from app.routers import assets, threats, risk, mitigations, report

app = FastAPI(title="Automotive Cybersecurity TARA Assistant")


@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)
    load_knowledge_base()


app.include_router(assets.router)
app.include_router(threats.router)
app.include_router(risk.router)
app.include_router(mitigations.router)
app.include_router(report.router)


@app.get("/")
def root():
    return {"status": "TARA Assistant backend is running"}
