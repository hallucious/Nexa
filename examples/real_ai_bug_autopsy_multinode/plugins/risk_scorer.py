
def weight(severity):
    return {"low":1,"medium":2,"high":4}[severity]

def mult(t):
    return {"governance":1.5,"financial":1.3,"operational":1.2,"sentiment":1.0}[t]

def conf(c):
    return {"low":0.7,"medium":1.0,"high":1.2}[c]

def run(input_data):
    flags = input_data["risk_flags"]
    score = 0
    for f in flags:
        s = weight(f["severity"]) * mult(f["type"]) * conf(f["confidence"])
        if f["direction"] == "positive":
            s *= -0.7
        score += s
    return {"risk_score": round(score,2)}
