
def normalize(text):
    return {"normalized": text.lower()}

def score(analysis):
    score = len(analysis) % 10
    return {"score": score}

def decision(score):
    if score < 5:
        return {"final_decision": "invest"}
    else:
        return {"final_decision": "do_not_invest"}
