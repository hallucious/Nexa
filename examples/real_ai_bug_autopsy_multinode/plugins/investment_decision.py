
def run(input_data):
    s = input_data["risk_score"]
    if s < 3:
        d="INVEST"
    elif s < 6:
        d="WATCHLIST"
    elif s < 7:
        d="REVIEW"
    else:
        d="DO NOT INVEST"
    return {"decision": d, "risk_score": s}
