import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./senai_crm.db")
MODEL_NAME = "llama-3.3-70b-versatile"

# Heuristic keywords
URGENCY_KEYWORDS = [
    "urgent", "p0", "critical", "emergency", "immediately", "asap",
    "legal", "cease and desist", "lawsuit", "ransomware", "breach",
    "escalate", "sla breach", "down", "outage"
]

SPAM_KEYWORDS = [
    "nigerian prince", "lottery", "winner", "free money", "click here",
    "buy now", "limited offer", "make money fast", "work from home",
    "seo services", "guaranteed results", "increase your ranking"
]

SECURITY_KEYWORDS = [
    "ransomware", "bitcoin", "btc", "hack", "breach", "suspicious login",
    "unauthorized access", "malware", "virus", "extort", "publish data"
]

LEGAL_KEYWORDS = [
    "cease and desist", "lawsuit", "legal action", "attorney", "lawyer",
    "sue", "court", "gdpr", "article 20", "data portability", "legal threat"
]

SPAM_DOMAINS = [
    "spam.com", "bulk-email.com", "marketing-blast.com"
]