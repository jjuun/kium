"""
주식자동매매프로그램 설정 파일
"""
import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

class Config:
    # 기본 설정
    DEBUG = True
    LOG_LEVEL = "INFO"
    
    # 거래 설정
    SYMBOL = "A005935"  # 삼성전자우
    EXCHANGE = "KRX"   # 한국거래소
    
    # 매매 전략 설정
    STRATEGY = "SMA_CROSSOVER"  # 이동평균선 교차 전략
    SHORT_PERIOD = 5    # 단기 이동평균 기간
    LONG_PERIOD = 20    # 장기 이동평균 기간
    
    # 리스크 관리 설정
    MAX_POSITION_SIZE = 1000000  # 최대 포지션 크기 (원)
    STOP_LOSS_PERCENT = 2.0      # 손절 비율 (%)
    TAKE_PROFIT_PERCENT = 5.0    # 익절 비율 (%)
    
    # API 설정 (실제 거래소 API 키 필요)
    API_KEY = os.getenv("API_KEY", "")
    API_SECRET = os.getenv("API_SECRET", "")
    API_URL = os.getenv("API_URL", "")
    
    # 키움증권 API 설정
    KIWOOM_APPKEY = os.getenv("KIWOOM_APPKEY", "a1FNKyL3TD9HSVujmYqoCeZpHYiAOoERGyd7eiCSDos")
    KIWOOM_SECRETKEY = os.getenv("KIWOOM_SECRETKEY", "qd1MDzpi55OLdCc8uNnf_LRMN9TaIi27PsM8QsE1OU8")
    KIWOOM_ACCOUNT_NO = os.getenv("KIWOOM_ACCOUNT_NO", "")
    KIWOOM_ACCOUNT_PRODUCT_CD = os.getenv("KIWOOM_ACCOUNT_PRODUCT_CD", "")
    KIWOOM_IS_SIMULATION = os.getenv("KIWOOM_IS_SIMULATION", "false").lower() == "true"
    
    # 데이터베이스 설정
    DATABASE_URL = "sqlite:///trading_data.db"
    
    # 로깅 설정
    LOG_FILE = "trading.log"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # 거래 시간 설정
    TRADING_START_TIME = "09:00"
    TRADING_END_TIME = "15:30"
    
    # 데이터 수집 설정
    DATA_INTERVAL = "1m"  # 1분봉
    HISTORY_DAYS = 30     # 과거 데이터 수집 기간 