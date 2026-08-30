from pydantic import BaseModel
from typing import List, Optional

class SafetyContext(BaseModel):
    is_night: bool
    incident_types: List[str]
    safety_score: int

class SafetyAssistant:
    @staticmethod
    def generate_advice(context: SafetyContext) -> str:
        """ Generuje lidsky srozumitelné bezpečnostní doporučení. """
        if context.safety_score >= 85:
            return "Trasa je vyhodnocena jako velmi bezpečná. Můžete jít bez obav."
        
        advice = []
        if context.is_night:
            advice.append("Doporučujeme mít po ruce rozsvícenou svítilnu a jít po osvětleném chodníku.")
            
        if "lighting_issue" in context.incident_types:
            advice.append("Na trase je nahlášena nefunkční pouliční lampa – vyhněte se temným koutům.")
            
        if "crime_violent" in context.incident_types or "suspicious_activity" in context.incident_types:
            advice.append("V oblasti bylo nahlášeno zvýšené riziko. Zvažte sdílení živé polohy s osobou blízko vás.")

        return " ".join(advice) if advice else "Zvýšená opatrnost je na místě. Sledujte své okolí."
