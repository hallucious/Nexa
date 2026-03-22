"""Demo plugins for investment_demo.nex savefile.

These are simple deterministic plugins demonstrating the v2.0.0
savefile execution model.
"""

from typing import Any, Dict


def extract_metrics(report: Dict[str, Any]) -> Dict[str, Any]:
    """Extract metrics from quarterly report.
    
    Args:
        report: Quarterly report data
        
    Returns:
        Dict with revenue and growth
    """
    return {
        "revenue": report.get("revenue", 0),
        "growth": report.get("growth_rate", 0.0),
    }


def calculate_score(revenue: float, growth: float) -> Dict[str, Any]:
    """Calculate investment score based on revenue and growth.
    
    Args:
        revenue: Company revenue
        growth: Growth rate (0.0 to 1.0)
        
    Returns:
        Dict with score (0-100)
    """
    # Simple scoring formula
    revenue_score = min(revenue / 1000000 * 50, 50)
    growth_score = min(growth * 100 * 50, 50)
    total_score = revenue_score + growth_score
    
    return {
        "score": round(total_score, 2)
    }


def make_decision(score: float, threshold: float) -> Dict[str, Any]:
    """Make investment decision based on score and threshold.
    
    Args:
        score: Investment score (0-100)
        threshold: Minimum acceptable score
        
    Returns:
        Dict with decision ("invest" or "pass")
    """
    decision = "invest" if score >= threshold else "pass"
    return {
        "decision": decision,
        "score": score,
        "threshold": threshold,
    }
