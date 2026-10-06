"""Evaluation of the TARA Assistant. Run from the project root:

    python -m evaluation.run_evaluation            # retrieval + risk tests only (no LLM needed)
    python -m evaluation.run_evaluation --llm      # also evaluates LLM steps (needs Ollama running)

Writes results to evaluation/results/evaluation_results.json and sample_outputs.md
"""
import argparse
import json
import os
import re
import time

from app.services import knowledge_base as kb
from app.services.risk_scoring import compute_risk_level

HERE = os.path.dirname(__file__)
OUT_DIR = os.path.join(HERE, "results")
GT = json.load(open(os.path.join(HERE, "ground_truth.json"), encoding="utf-8"))
THREATS = json.load(open(os.path.join(kb.DATA_DIR, "threats.json"), encoding="utf-8"))
MITIGATIONS = json.load(open(os.path.join(kb.DATA_DIR, "mitigations.json"), encoding="utf-8"))
MIT_IDS = {m["id"] for m in MITIGATIONS}
ARCH_COMPONENTS = {
    "Telematics Control Unit (TCU)": ["tcu", "telematics"],
    "Infotainment ECU": ["infotainment"],
    "Gateway ECU": ["gateway"],
    "Diagnostic Port (UDS)": ["diagnostic"],
    "Backend Cloud Server": ["backend", "cloud"],
}


def arch_description(name):
    """Pull the component's description line out of the architecture document."""
    for line in kb.architecture_full_text.splitlines():
        if re.match(r"^\d+\. " + re.escape(name.split(" (")[0]), line):
            return line.split(" - ", 1)[-1]
    return name


def eval_risk():
    ok = 0
    for key, exp in GT["risk_matrix_expected"].items():
        i, f = key.split(",")
        ok += compute_risk_level(i, f) == exp
    n = len(GT["risk_matrix_expected"])
    return {"cases": n, "correct": ok, "accuracy": ok / n}


def eval_threat_retrieval():
    rows, hit1, hit3, hit5, rr = [], 0, 0, 0, 0
    for item in GT["threat_retrieval_questions"]:
        ids = [r["metadata"]["threat_id"] for r in kb.threat_store.search(item["q"], top_k=5)]
        rank = ids.index(item["expected"]) + 1 if item["expected"] in ids else None
        hit1 += rank == 1
        hit3 += bool(rank and rank <= 3)
        hit5 += rank is not None
        rr += 1 / rank if rank else 0
        rows.append({"question": item["q"], "expected": item["expected"], "retrieved": ids, "rank": rank})
    n = len(rows)
    return {"questions": n, "hit@1": hit1 / n, "hit@3": hit3 / n, "hit@5": hit5 / n, "MRR": rr / n, "rows": rows}


def eval_mitigation_retrieval():
    rows, hit1, hit3, rr = [], 0, 0, 0
    for t in THREATS:
        res = kb.mitigation_store.search(f"{t['name']}: {t['description']}", top_k=3)
        ids = [r["metadata"]["mitigation_id"] for r in res]
        expected = next(m["id"] for m in MITIGATIONS if m["threat_ref"] == t["id"])
        rank = ids.index(expected) + 1 if expected in ids else None
        hit1 += rank == 1
        hit3 += rank is not None
        rr += 1 / rank if rank else 0
        rows.append({"threat": t["id"], "expected": expected, "retrieved": ids, "rank": rank})
    n = len(rows)
    return {"threats": n, "hit@1": hit1 / n, "hit@3": hit3 / n, "MRR": rr / n, "rows": rows}


def eval_asset_retrieval_recall():
    """Retrieval step only: do the top-5 retrieved threats for each asset contain the gold threats?"""
    rows, found, total = [], 0, 0
    for asset, gold in GT["assets"].items():
        ids = [r["metadata"]["threat_id"] for r in kb.threat_store.search(arch_description(asset), top_k=5)]
        hit = [g for g in gold if g in ids]
        found += len(hit)
        total += len(gold)
        rows.append({"asset": asset, "gold": gold, "retrieved": ids, "recall": len(hit) / len(gold)})
    return {"recall@5": found / total, "rows": rows}


def eval_llm():
    from app.services.ai_tasks import (extract_assets_from_text, generate_threats_for_asset,
                                       suggest_mitigation_for_threat)
    out = {}
    t0 = time.time()

    # 1. Asset extraction
    extracted = extract_assets_from_text(kb.architecture_full_text)
    names = " ".join((a.get("name", "") + " " + a.get("description", "")).lower() for a in extracted)
    found = {k: any(w in names for w in v) for k, v in ARCH_COMPONENTS.items()}
    out["asset_extraction"] = {"extracted_count": len(extracted), "gold_components_found": found,
                               "recall": sum(found.values()) / len(found), "raw": extracted}

    # 2. Threat selection (RAG) per gold asset
    tp = fp = fn = invalid = total_sel = 0
    thr_rows = []
    for asset, gold in GT["assets"].items():
        desc = arch_description(asset)
        retrieved = kb.threat_store.search(desc, top_k=5)
        retrieved_ids = {r["metadata"]["threat_id"] for r in retrieved}
        sugg = generate_threats_for_asset(asset, desc, retrieved)
        sel = [s.get("threat_id") for s in sugg if isinstance(s, dict)]
        total_sel += len(sel)
        invalid += sum(1 for s in sel if s not in retrieved_ids)  # the app's guardrail drops these
        valid = {s for s in sel if s in retrieved_ids}
        tp += len(valid & set(gold))
        fp += len(valid - set(gold))
        fn += len(set(gold) - valid)
        thr_rows.append({"asset": asset, "gold": gold, "selected": sel, "suggestions": sugg})
    prec = tp / (tp + fp) if tp + fp else 0
    rec = tp / (tp + fn) if tp + fn else 0
    out["threat_selection"] = {"precision": prec, "recall": rec,
                               "f1": 2 * prec * rec / (prec + rec) if prec + rec else 0,
                               "ids_outside_retrieved_set": invalid, "total_selected": total_sel,
                               "citation_validity": 1 - invalid / total_sel if total_sel else 0,
                               "rows": thr_rows}

    # 3. Mitigation suggestion per threat
    ok_cite = exact = 0
    mit_rows = []
    for t in THREATS:
        retrieved = kb.mitigation_store.search(f"{t['name']}: {t['description']}", top_k=3)
        res = suggest_mitigation_for_threat(t["name"], t["description"], retrieved, t["id"])
        mid = res.get("mitigation_id") if isinstance(res, dict) else None
        expected = next(m["id"] for m in MITIGATIONS if m["threat_ref"] == t["id"])
        ok_cite += mid in MIT_IDS
        exact += mid == expected
        mit_rows.append({"threat": t["id"], "expected": expected, "cited": mid, "result": res})
    n = len(THREATS)
    out["mitigation_suggestion"] = {"valid_citation_rate": ok_cite / n, "correct_mitigation_rate": exact / n,
                                    "rows": mit_rows}
    out["llm_seconds"] = round(time.time() - t0, 1)
    return out


def write_samples(res):
    lines = ["# Sample Outputs (auto-generated by run_evaluation.py)\n"]
    for r in res["threat_retrieval"]["rows"][:4]:
        lines.append(f"**Q:** {r['question']}  \n**Retrieved (top-5 threat IDs, citation = threats.json):** "
                     f"{r['retrieved']}  \n**Expected:** {r['expected']} (rank {r['rank']})\n")
    if "llm" in res:
        for r in res["llm"]["threat_selection"]["rows"][:3]:
            lines.append(f"### Asset: {r['asset']}\nGold: {r['gold']}  \nLLM selected: {r['selected']}\n")
            for s in r["suggestions"]:
                lines.append(f"- {s.get('threat_id')} - {s.get('reasoning')} _(Source: threats.json {s.get('threat_id')})_")
            lines.append("")
        for r in res["llm"]["mitigation_suggestion"]["rows"][:4]:
            lines.append(f"- Threat {r['threat']} -> {r['result']} _(expected {r['expected']})_")
    open(os.path.join(OUT_DIR, "sample_outputs.md"), "w", encoding="utf-8").write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true")
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    kb.load_knowledge_base()
    res = {"risk_matrix": eval_risk(), "threat_retrieval": eval_threat_retrieval(),
           "asset_threat_retrieval": eval_asset_retrieval_recall(),
           "mitigation_retrieval": eval_mitigation_retrieval()}
    if args.llm:
        from app.services.llm_service import MODEL_NAME
        res["model"] = MODEL_NAME
        res["llm"] = eval_llm()
    json.dump(res, open(os.path.join(OUT_DIR, "evaluation_results.json"), "w", encoding="utf-8"), indent=2)
    write_samples(res)

    def show(d):
        return {k: round(v, 3) for k, v in d.items() if isinstance(v, float)}
    print("Risk matrix:", res["risk_matrix"])
    print("Threat retrieval (12 questions):", show(res["threat_retrieval"]))
    print("Asset->threat recall@5:", round(res["asset_threat_retrieval"]["recall@5"], 3))
    print("Mitigation retrieval:", show(res["mitigation_retrieval"]))
    if args.llm:
        l = res["llm"]
        print("Asset extraction: recall", l["asset_extraction"]["recall"], "count", l["asset_extraction"]["extracted_count"])
        print("Threat selection:", show(l["threat_selection"]))
        print("Mitigation suggestion:", show(l["mitigation_suggestion"]))
        print("LLM time (s):", l["llm_seconds"])


if __name__ == "__main__":
    main()
