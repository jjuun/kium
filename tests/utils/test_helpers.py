"""
테스트 헬퍼 함수들
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List

def create_mock_stock_data(
    symbol: str = "005935",
    days: int = 30,
    base_price: int = 50000
) -> pd.DataFrame:
    """모의 주식 데이터 생성"""
    dates = pd.date_range(
        start=datetime.now() - timedelta(days=days),
        end=datetime.now(),
        freq='D'
    )
    
    # 가격 변동 시뮬레이션
    prices = []
    current_price = base_price
    
    for _ in range(len(dates)):
        # -5% ~ +5% 랜덤 변동
        change_pct = np.random.uniform(-0.05, 0.05)
        current_price = int(current_price * (1 + change_pct))
        prices.append(current_price)
    
    data = pd.DataFrame({
        '종가': prices,
        '시가': [p * 0.99 for p in prices],
        '고가': [p * 1.02 for p in prices],
        '저가': [p * 0.98 for p in prices],
        '거래량': np.random.randint(500000, 2000000, len(dates))
    }, index=dates)
    
    return data

def create_mock_trading_signal(
    symbol: str = "005935",
    signal_type: str = "buy",
    price: int = 50000,
    confidence: float = 0.8
) -> Dict[str, Any]:
    """모의 거래 신호 생성"""
    return {
        'symbol': symbol,
        'signal_type': signal_type,
        'condition_id': 1,
        'condition_value': 'RSI < 30',
        'current_price': price,
        'timestamp': datetime.now(),
        'confidence': confidence,
        'reason': ['RSI 과매도', '이동평균선 지지']
    }

def create_mock_api_response(
    response_type: str = "stock_price",
    success: bool = True
) -> Dict[str, Any]:
    """모의 API 응답 생성"""
    if response_type == "stock_price":
        return {
            'success': success,
            'output': [
                {
                    'prpr': '50000',
                    'prdy_vrss': '-1000',
                    'prdy_ctrt': '-1.96',
                    'acml_tr_pbmn': '1000000',
                    'acml_vol': '1000000'
                }
            ]
        }
    elif response_type == "token":
        return {
            'success': success,
            'access_token': 'test_token_12345',
            'expires_in': 3600,
            'token_type': 'Bearer'
        }
    else:
        return {'success': success}

def assert_dataframe_structure(df: pd.DataFrame, expected_columns: List[str]):
    """DataFrame 구조 검증"""
    assert isinstance(df, pd.DataFrame), "DataFrame이 아닙니다"
    assert len(df) > 0, "빈 DataFrame입니다"
    
    for col in expected_columns:
        assert col in df.columns, f"컬럼 '{col}'이 없습니다"

def assert_trading_signal_structure(signal: Dict[str, Any]):
    """거래 신호 구조 검증"""
    required_keys = [
        'symbol', 'signal_type', 'current_price', 
        'timestamp', 'confidence'
    ]
    
    for key in required_keys:
        assert key in signal, f"필수 키 '{key}'가 없습니다"
    
    assert signal['signal_type'] in ['buy', 'sell'], "잘못된 신호 타입"
    assert 0 <= signal['confidence'] <= 1, "신뢰도는 0~1 사이여야 합니다"
    assert signal['current_price'] > 0, "가격은 양수여야 합니다"

def create_mock_database_connection():
    """모의 데이터베이스 연결 생성"""
    class MockConnection:
        def __init__(self):
            self.executed_queries = []
            self.results = []
        
        def execute(self, query, params=None):
            self.executed_queries.append((query, params))
            return self
        
        def fetchall(self):
            return self.results
        
        def commit(self):
            pass
        
        def close(self):
            pass
    
    return MockConnection() 