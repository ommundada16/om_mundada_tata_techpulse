import json
import os
from app.services.chunker import chunk_text
from app.services.vector_store import SimpleVectorStore

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

architecture_store = SimpleVectorStore()
threat_store = SimpleVectorStore()
mitigation_store = SimpleVectorStore()

architecture_full_text = ""


def load_knowledge_base():
    """Runs once when the server starts: reads the synthetic data files, chunks/embeds them,
    and stores them in the three vector stores (architecture, threats, mitigations)."""
    global architecture_full_text

    # 1. Architecture document -> chunk + embed
    arch_path = os.path.join(DATA_DIR, "architecture.txt")
    with open(arch_path, "r", encoding="utf-8") as f:
        architecture_full_text = f.read()

    chunks = chunk_text(architecture_full_text)
    architecture_store.add([
        {"id": f"chunk_{i}", "text": chunk, "metadata": {"chunk_index": i}}
        for i, chunk in enumerate(chunks)
    ])

    # 2. Threat library -> embed each threat separately
    threats_path = os.path.join(DATA_DIR, "threats.json")
    with open(threats_path, "r", encoding="utf-8") as f:
        threats = json.load(f)

    threat_store.add([
        {
            "id": t["id"],
            "text": f"{t['name']}: {t['description']}",
            "metadata": {
                "threat_id": t["id"],
                "name": t["name"],
                "applicable_interface": t["applicable_interface"],
            },
        }
        for t in threats
    ])

    # 3. Mitigation library -> embed each mitigation separately
    mitigations_path = os.path.join(DATA_DIR, "mitigations.json")
    with open(mitigations_path, "r", encoding="utf-8") as f:
        mitigations = json.load(f)

    mitigation_store.add([
        {
            "id": m["id"],
            "text": m["description"],
            "metadata": {"mitigation_id": m["id"], "threat_ref": m["threat_ref"]},
        }
        for m in mitigations
    ])

    print(
        f"Knowledge base loaded: {len(chunks)} architecture chunks, "
        f"{len(threats)} threats, {len(mitigations)} mitigations."
    )
