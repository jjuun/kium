"""
pytest 설정 및 공통 fixtures
"""
import sys
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 테스트용 샘플 데이터
@pytest.fixture
def sample_stock_data():
    """샘플 주식 데이터 fixture"""
    dates = pd.date_range(start='2025-07-15', end='2025-07-22', freq='D')
    data = pd.DataFrame({
        '종가': [50000, 51000, 52000, 53000, 54000, 53500, 54500, 55000],
        '시가': [49500, 50500, 51500, 52500, 53500, 53000, 54000, 54500],
        '고가': [51500, 52500, 53500, 54500, 55500, 55000, 56000, 56500],
        '저가': [49000, 50000, 51000, 52000, 53000, 52500, 53500, 54000],
        '거래량': [1000000, 1100000, 1200000, 1300000, 1400000, 1350000, 1450000, 1500000]
    }, index=dates)
    return data

@pytest.fixture
def sample_trading_signal():
    """샘플 거래 신호 fixture"""
    return {
        'symbol': '005935',
        'signal_type': 'buy',
        'condition_id': 1,
        'condition_value': 'RSI < 30',
        'current_price': 50000,
        'timestamp': datetime.now(),
        'confidence': 0.85
    }

@pytest.fixture
def mock_kiwoom_api_response():
    """키움 API 응답 모킹 fixture"""
    return {
        'access_token': 'test_token_12345',
        'expires_in': 3600,
        'token_type': 'Bearer'
    }

@pytest.fixture
def mock_stock_price_response():
    """주식 가격 API 응답 모킹 fixture"""
    return {
        'output': [
            {
                'prpr': '50000',  # 현재가
                'prdy_vrss': '-1000',  # 전일 대비
                'prdy_ctrt': '-1.96',  # 전일 대비율
                'acml_tr_pbmn': '1000000',  # 누적 거래량
                'acml_vol': '1000000'  # 누적 거래대금
            }
        ]
    }

@pytest.fixture
def test_db_path(tmp_path):
    """테스트용 데이터베이스 경로 fixture"""
    return str(tmp_path / "test_auto_trading.db")

@pytest.fixture
def mock_logger():
    """로거 모킹 fixture"""
    with patch('src.core.logger.logger') as mock_logger:
        yield mock_logger

@pytest.fixture
def mock_requests():
    """requests 모킹 fixture"""
    with patch('requests.get') as mock_get, \
         patch('requests.post') as mock_post:
        yield {
            'get': mock_get,
            'post': mock_post
        }

# 테스트 마커 등록
def pytest_configure(config):
    """pytest 설정"""
    config.addinivalue_line(
        "markers", "unit: 단위 테스트"
    )
    config.addinivalue_line(
        "markers", "integration: 통합 테스트"
    )
    config.addinivalue_line(
        "markers", "e2e: 엔드투엔드 테스트"
    )
    config.addinivalue_line(
        "markers", "slow: 느린 테스트"
    )
    config.addinivalue_line(
        "markers", "api: API 테스트"
    )
    config.addinivalue_line(
        "markers", "database: 데이터베이스 테스트"
    ) 