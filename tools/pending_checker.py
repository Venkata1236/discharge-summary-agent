def check_pending_results(pending: list[str]) -> dict:
    """Mock pending result checker"""
    critical_keywords = ["culture", "biopsy", "sensitivity", "histology", "pcr"]
    critical = [
        p for p in pending
        if any(k in p.lower() for k in critical_keywords)
    ]
    return {
        "total_pending": len(pending),
        "critical_pending": critical,
        "message": f"{len(critical)} critical pending result(s) identified"
    }