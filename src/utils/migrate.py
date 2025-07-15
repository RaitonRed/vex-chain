from src.utils.database import init_db
from src.utils.logger import logger

def run_migrations():
    """اجرای تمام مهاجرت‌های دیتابیس"""
    logger.info("Running database migrations...")
    try:
        init_db()
        logger.info("Migrations completed successfully")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

if __name__ == '__main__':
    run_migrations()