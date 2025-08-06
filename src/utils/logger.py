import logging
import colorlog
import colorama
import os
from datetime import datetime

colorama.init()

def setup_logger():
    """تنظیمات پیشرفته برای سیستم لاگینگ با پشتیبانی از رنگ"""
    os.makedirs("logs", exist_ok=True)
    
    log_file = f"logs/blockchain_{datetime.now().strftime('%Y%m%d')}.log"
    
    # فرمت‌دهنده رنگ‌آمیز برای کنسول
    console_formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
            'EXCEPTION': 'red,bg_white'
        },
        secondary_log_colors={},
        style='%'
    )
    
    # فرمت‌دهنده ساده برای فایل
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # هندلرهای مختلف
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(file_formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    
    # ایجاد لاگر اصلی
    logger = logging.getLogger('Blockchain')
    logger.setLevel(logging.INFO)
    
    # اضافه کردن هندلرها
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logger()


def debug(msg, *args, **kwargs):
    logger.debug(msg, *args, **kwargs)

def info(msg, *args, **kwargs):
    logger.info(msg, *args, **kwargs)

def warning(msg, *args, **kwargs):
    logger.warning(msg, *args, **kwargs)

def error(msg, *args, **kwargs):
    logger.error(msg, *args, **kwargs)

def critical(msg, *args, **kwargs):
    logger.critical(msg, *args, **kwargs)

def exception(msg, *args, **kwargs):
    logger.exception(msg, *args, **kwargs)