import structlog
from src.dlp_processor import dlp_redactor


def configure_logger():
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            dlp_redactor,  # Redact PII before rendering
            structlog.processors.JSONRenderer() # FAANG standard: Pure JSON
        ],
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger()

logger = configure_logger()
