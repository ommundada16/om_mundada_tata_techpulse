"""End-to-end run of the full TARA workflow through the REST API (backend must be running on port 8000).
Saves the transcript to evaluation/results/e2e_run_log.md - used as evidence in the report/video.
"""
import os
import requests

API = "http://localhost:8000"
OUT = os.path.join(os.path.dirname(__file__), "results", "e2e_run_log.md")
log = ["# End-to-end run log (API)\n"]


def step(title, data):
    log.append(f"## {title}\n```\n{data}\n```\n")
    print(title)


assets = requests.post(f"{API}/assets/extract", timeout=300).json()
step("1. Extract assets (LLM)", "\n".join(f"{a['id']}: {a['name']} [{a['interface_type']}] status={a['status']}" for a in assets))

target = next((a for a in assets if "gateway" in a["name"].lower()), assets[0])
threats = requests.post(f"{API}/threats/generate/{target['id']}", timeout=300).json()
step(f"2. Generate threats for '{target['name']}' (RAG + LLM, with citations)",
     "\n".join(f"{t['id']}: {t['name']} | reasoning: {t['reasoning']} | citation: {t['source_citation']}" for t in threats))

first = threats[0]
risk = requests.post(f"{API}/risk/assess", json={"threat_scenario_id": first["id"], "impact": "HIGH",
                                                  "feasibility": "MEDIUM", "assessed_by": "engineer"}).json()
step("3. Risk assessment (deterministic matrix, human supplies Impact/Feasibility)",
     f"threat {first['id']}: Impact=HIGH, Feasibility=MEDIUM -> {risk['risk_level']}")

mit = requests.post(f"{API}/mitigations/suggest/{first['id']}", timeout=300).json()
step("4. Suggest mitigation (RAG + LLM)", f"{mit['mitigation_library_ref']}: {mit['description']} | status={mit['status']}")

appr = requests.post(f"{API}/mitigations/{mit['id']}/approve", json={"approved_by": "reviewer"}).json()
step("5. Human approval", f"status={appr['status']} approved_by={appr['approved_by']}")

rep = requests.get(f"{API}/report/traceability").json()
step("6. Traceability report (Asset -> Threat -> Risk -> Mitigation)",
     "\n".join(f"{r['asset']} | {r['threat']} | {r['risk_level']} | {r['mitigation_status']}" for r in rep))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w", encoding="utf-8").write("\n".join(log))
print("saved", OUT)
