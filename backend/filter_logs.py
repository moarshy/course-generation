import logging
import sys

# Set LiteLLM logging to WARNING level to reduce noise
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Also filter out specific loggers that are noisy
for logger_name in ["litellm", "httpx", "openai", "httpcore"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

# Set root logger level
logging.basicConfig(level=logging.INFO)
