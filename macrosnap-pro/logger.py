import logging
import time
import sys
from functools import wraps

# Centralized application logging
logger = logging.getLogger("MacroSnap")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def log_execution_time(func):
    """Decorator to track performance of expensive operations."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            status = "SUCCESS"
        except Exception as e:
            status = f"FAILED ({str(e)})"
            raise e
        finally:
            duration = round((time.time() - start_time) * 1000, 2)
            logger.info(f"[{func.__name__}] {status} in {duration} ms")
        return result
    return wrapper
