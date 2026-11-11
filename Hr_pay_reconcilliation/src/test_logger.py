import logging


# 1. Initialize your custom loggers
logger = logging.getLogger("pipeline")
audit_logger = logging.getLogger("audit")

# Set their individual tracking levels

audit_logger.setLevel(logging.INFO)

# 2. CRITICAL: Stop logs from bubbling up to the default console handler
logger.propagate = False
audit_logger.propagate = False

p_handler = logging.FileHandler("logs/pipeline_errors.log")
p_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
logger.addHandler(p_handler)
# Handler for "audit" -> audit.log
a_handler = logging.FileHandler("logs/ingestion_audit.log")
a_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
audit_logger.addHandler(a_handler)


# --- TEST IT OUT ---
if __name__ == "__main__":
    logger.info("This is an app pipeline event.")
    audit_logger.info("This is a sensitive security audit event.")
