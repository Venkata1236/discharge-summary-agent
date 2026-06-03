def flag_for_review(flags: list[str], conflicts: list[str]) -> dict:
    """Mock escalation tool — flags summary for clinician review"""
    total = len(flags) + len(conflicts)
    return {
        "message": f"Summary flagged for clinician review — {total} item(s) require attention",
        "total_flags": len(flags),
        "total_conflicts": len(conflicts),
        "status": "escalated"
    }