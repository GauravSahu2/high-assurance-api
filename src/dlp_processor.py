import re
import structlog

# Regex patterns for common PII
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
CREDIT_CARD_PATTERN = re.compile(r'\b(?:\d[ -]*?){13,16}\b')
SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
AUTH_HEADER_PATTERN = re.compile(r'(?i)(Authorization|api-key):\s*(Bearer\s+)?[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*')

def dlp_redactor(logger, method_name, event_dict):
    """
    DLP (Data Loss Prevention) processor for structlog.
    Redacts PII patterns from all values in the event_dict.
    """
    for key, value in event_dict.items():
        if isinstance(value, str):
            # Redact Emails
            value = EMAIL_PATTERN.sub("[EMAIL_REDACTED]", value)
            # Redact Credit Cards
            value = CREDIT_CARD_PATTERN.sub("[CREDIT_CARD_REDACTED]", value)
            # Redact SSNs
            value = SSN_PATTERN.sub("[SSN_REDACTED]", value)
            # Redact Auth Tokens/Keys
            value = AUTH_HEADER_PATTERN.sub(r"\1: [REDACTED]", value)
            
            event_dict[key] = value
            
    return event_dict
