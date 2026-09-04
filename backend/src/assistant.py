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
            
        if "poor_lighting" in context.incident_types:
            advice.append("Na trase je nahlášena nefunkční pouliční lampa – vyhněte se temným koutům.")

        if "violence" in context.incident_types or "suspicious_activity" in context.incident_types:
            advice.append("V oblasti bylo nahlášeno zvýšené riziko. Zvažte sdílení živé polohy s osobou blízko vás.")

        if "harassment" in context.incident_types:
            advice.append("V oblasti bylo nahlášeno obtěžování. Zvažte alternativní trasu nebo doprovod.")

        if "theft" in context.incident_types:
            advice.append("V okolí bylo nahlášeno krádeže – mějte cennosti mimo dohled.")

        return " ".join(advice) if advice else "Zvýšená opatrnost je na místě. Sledujte své okolí."
