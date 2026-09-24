import logging
import json
import datetime
from typing import Any, Dict

class JSONFormatter(logging.Formatter):
    """
    Structured JSON log formatter as required by LISA specifications:
    {
      "timestamp": "...",
      "run_id": "...",
      "agent": "...",
      "action": "...",
      "status": "...",
      "duration": 0.0,
      "error": "..."
    }
    """
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Attach structured fields if present in record
        for field in ["run_id", "agent", "action", "status", "target", "duration", "error"]:
            if hasattr(record, field):
                log_data[field] = getattr(record, field)
                
        if record.exc_info:
            log_data["error"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)

def setup_logging(log_level: str = "INFO"):
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Clear handlers
    logger.handlers = []
    
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    
    return logger

logger = setup_logging()
