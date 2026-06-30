import logging
import sys

def setup_logger() -> logging.Logger:
    """
    Sets up and configures the logger for the pipeline.
    """
    logger = logging.getLogger("CandidateTransformer")
    logger.setLevel(logging.INFO)
    
    # Ensure handlers are not duplicated
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s [%(name)s]: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger
