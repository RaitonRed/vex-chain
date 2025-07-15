import logging
import os
from datetime import datetime

def setup_logger():
    """تنظیمات اولیه برای سیستم لاگینگ"""
    os.makedirs("logs", exist_ok=True)
    
    log_file = f"logs/blockchain_{datetime.now().strftime('%Y%m%d')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger('Blockchain')

logger = setup_logger()