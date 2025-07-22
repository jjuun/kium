"""
로깅 시스템 설정
"""

import logging
import os
from datetime import datetime
from src.core.config import Config


def setup_logger(name="TradingBot"):
    """
    로거 설정
    """
    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, Config.LOG_LEVEL))

    # 이미 핸들러가 설정되어 있다면 추가하지 않음
    if logger.handlers:
        return logger

    # 포맷터 설정
    formatter = logging.Formatter(Config.LOG_FORMAT)

    # 파일 핸들러 설정
    if not os.path.exists("logs"):
        os.makedirs("logs")

    file_handler = logging.FileHandler(f"logs/{Config.LOG_FILE}")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# 기본 로거 생성
logger = setup_logger()
