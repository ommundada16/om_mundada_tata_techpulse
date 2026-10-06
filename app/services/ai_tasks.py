from app.services.llm_service import call_llm, extract_json

ASSETS_SCHEMA = {"type": "object", "properties": {"assets": {"type": "array", "items": {"type": "object", "properties": {
    "name": {"type": "string"}, "description": {"type": "string"}, "interface_type": {"type": "string"}},
    "required": ["name", "description", "interface_type"]}}}, "required": ["assets"]}

THREATS_SCHEMA = {"type": "object", "properties": {"threats": {"type": "array", "items": {"type": "object", "properties": {
    "threat_id": {"type": "string"}, "reasoning": {"type": "string"}},
    "required": ["threat_id", "reasoning"]}}}, "required": ["threats"]}

MITIGATION_SCHEMA = {"type": "object", "properties": {"mitigation_id": {"type": "string"}, "description": {"type": "string"}},
                     "required": ["mitigation_id", "description"]}


def extract_assets_from_text(document_text: str):
    prompt = f"""You are a cybersecurity analyst. Read the system architecture below and list every asset
(component, interface, or data flow) that could be a target or attack surface.

Architecture:
{document_text}

Respond with ONLY a JSON object, no other text, in this exact format:
{{"assets": [{{"name": "...", "description": "...", "interface_type": "CAN/OTA/Bluetooth/Backend API/Diagnostic Port"}}]}}
"""
    reply = call_llm(prompt, ASSETS_SCHEMA)
    result = extract_json(reply)
    return result.get("assets", []) if isinstance(result, dict) else []


def generate_threats_for_asset(asset_name: str, asset_description: str, retrieved_threats: list[dict]):
    threat_list_text = "\n".join(
        f"- {t['metadata']['threat_id']}: {t['text']}" for t in retrieved_threats
    )
    prompt = f"""You are a cybersecurity analyst performing a Threat Analysis and Risk Assessment (TARA).

Asset: {asset_name}
Description: {asset_description}

Here are known threat patterns that might apply:
{threat_list_text}

Using ONLY the threats listed above (do not invent new threats), decide which ones realistically apply
to this asset and explain why in one sentence each.

Respond with ONLY a JSON object in this exact format:
{{"threats": [{{"threat_id": "T001", "reasoning": "..."}}]}}
"""
    reply = call_llm(prompt, THREATS_SCHEMA)
    result = extract_json(reply)
    return result.get("threats", []) if isinstance(result, dict) else []


def suggest_mitigation_for_threat(threat_name: str, threat_description: str, retrieved_mitigations: list[dict],
                                  threat_id: str = ""):
    mitigation_list_text = "\n".join(
        f"- {m['metadata']['mitigation_id']} (designed for threat {m['metadata']['threat_ref']}): {m['text']}"
        for m in retrieved_mitigations
    )
    prompt = f"""You are a cybersecurity engineer drafting a mitigation recommendation.

Threat: {threat_id} {threat_name}
Description: {threat_description}

Here are known mitigation options that might apply:
{mitigation_list_text}

Using ONLY the mitigations listed above, prefer the one designed for this exact threat, and write a short recommended mitigation for this threat, and mention
which mitigation ID it is based on.

Respond with ONLY a JSON object in this exact format:
{{"mitigation_id": "M001", "description": "..."}}
"""
    reply = call_llm(prompt, MITIGATION_SCHEMA)
    result = extract_json(reply)
    return result if result else None
