def check_drug_interactions(med_names: list[str]) -> dict:
    """
    Mock drug interaction checker.
    Returns severity-graded interactions rather than a flat list —
    this is illustrative of where a real DrugBank/FDA API would sit.
    """
    known_interactions = {
        ("warfarin", "aspirin"): {"severity": "high", "note": "Increased bleeding risk"},
        ("metformin", "contrast"): {"severity": "high", "note": "Risk of lactic acidosis"},
        ("digoxin", "amiodarone"): {"severity": "high", "note": "Digoxin toxicity risk"},
        ("ace inhibitor", "potassium"): {"severity": "medium", "note": "Hyperkalemia risk"},
        ("nsaid", "ace inhibitor"): {"severity": "medium", "note": "Reduced renal function risk"},
        ("ssri", "nsaid"): {"severity": "medium", "note": "Increased GI bleeding risk"},
        ("statin", "clarithromycin"): {"severity": "high", "note": "Rhabdomyolysis risk"},
    }

    found = []
    names_lower = [n.lower() for n in med_names]

    for (drug1, drug2), details in known_interactions.items():
        if any(drug1 in n for n in names_lower) and any(drug2 in n for n in names_lower):
            found.append({
                "pair": f"{drug1} + {drug2}",
                "severity": details["severity"],
                "note": details["note"]
            })

    return {
        "interactions": found,
        "checked": med_names,
        "high_severity_count": sum(1 for f in found if f["severity"] == "high")
    }