def check_drug_interactions(med_names: list[str]) -> dict:
    """Mock drug interaction checker"""
    known_interactions = {
        ("warfarin", "aspirin"): "Warfarin + Aspirin — increased bleeding risk",
        ("metformin", "contrast"): "Metformin + Contrast — risk of lactic acidosis",
        ("digoxin", "amiodarone"): "Digoxin + Amiodarone — digoxin toxicity risk",
    }
    found = []
    names_lower = [n.lower() for n in med_names]
    for (drug1, drug2), message in known_interactions.items():
        if drug1 in names_lower and drug2 in names_lower:
            found.append(message)
    return {"interactions": found, "checked": med_names}