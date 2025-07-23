from src.utils.database import init_db
from src.utils.logger import logger
import os

def reset_database():
    logger.warning("Resetting database...")
    try:
        os.remove("data/blockchain.db")
        logger.info("Database file removed")
    except FileNotFoundError:
        logger.warning("Database file not found")
    
    init_db()
    logger.info("Database reinitialized")

if __name__ == '__main__':
    reset_database()