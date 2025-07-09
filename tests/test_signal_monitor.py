"""
신호 모니터링 시스템 테스트
"""
import unittest
import tempfile
import os
from datetime import datetime, timedelta
from src.auto_trading.signal_monitor import SignalMonitor, SignalStatus, SignalRecord

class TestSignalMonitor(unittest.TestCase):
    """신호 모니터링 테스트 클래스"""
    
    def setUp(self):
        """테스트 설정"""
        # 임시 데이터베이스 파일 생성
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.signal_monitor = SignalMonitor(self.temp_db.name)
    
    def tearDown(self):
        """테스트 정리"""
        # 임시 파일 삭제
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_init_database(self):
        """데이터베이스 초기화 테스트"""
        # 데이터베이스가 정상적으로 생성되었는지 확인
        self.assertTrue(os.path.exists(self.temp_db.name))
        
        # 테이블이 생성되었는지 확인
        import sqlite3
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='signal_history'")
            result = cursor.fetchone()
            self.assertIsNotNone(result)
    
    def test_record_signal(self):
        """신호 기록 테스트"""
        # 신호 기록
        signal_id = self.signal_monitor.record_signal(
            symbol="005930",  # 삼성전자
            signal_type="buy",
            condition_id=1,
            condition_value="RSI < 30",
            current_price=70000.0
        )
        
        # 신호 ID가 반환되었는지 확인
        self.assertGreater(signal_id, 0)
        
        # 기록된 신호 조회
        signals = self.signal_monitor.get_signals()
        self.assertEqual(len(signals), 1)
        
        signal = signals[0]
        self.assertEqual(signal.symbol, "005930")
        self.assertEqual(signal.signal_type, "buy")
        self.assertEqual(signal.condition_id, 1)
        self.assertEqual(signal.condition_value, "RSI < 30")
        self.assertEqual(signal.current_price, 70000.0)
        self.assertEqual(signal.status, SignalStatus.PENDING)
    
    def test_update_signal_execution(self):
        """신호 실행 정보 업데이트 테스트"""
        # 신호 기록
        signal_id = self.signal_monitor.record_signal(
            symbol="005930",
            signal_type="buy",
            condition_id=1,
            condition_value="RSI < 30",
            current_price=70000.0
        )
        
        # 실행 정보 업데이트
        success = self.signal_monitor.update_signal_execution(
            signal_id=signal_id,
            executed_price=70500.0,
            executed_quantity=10
        )
        
        self.assertTrue(success)
        
        # 업데이트된 신호 조회
        signals = self.signal_monitor.get_signals()
        signal = signals[0]
        self.assertEqual(signal.status, SignalStatus.EXECUTED)
        self.assertEqual(signal.executed_price, 70500.0)
        self.assertEqual(signal.executed_quantity, 10)
        self.assertIsNotNone(signal.executed_at)
    
    def test_close_signal(self):
        """신호 종료 테스트"""
        # 신호 기록 및 실행
        signal_id = self.signal_monitor.record_signal(
            symbol="005930",
            signal_type="buy",
            condition_id=1,
            condition_value="RSI < 30",
            current_price=70000.0
        )
        
        self.signal_monitor.update_signal_execution(
            signal_id=signal_id,
            executed_price=70500.0,
            executed_quantity=10
        )
        
        # 수익으로 종료
        success = self.signal_monitor.close_signal(signal_id, 50000.0)
        self.assertTrue(success)
        
        signals = self.signal_monitor.get_signals()
        signal = signals[0]
        self.assertEqual(signal.status, SignalStatus.SUCCESS)
        self.assertEqual(signal.profit_loss, 50000.0)
        self.assertIsNotNone(signal.closed_at)
        
        # 손실로 종료하는 경우도 테스트
        signal_id2 = self.signal_monitor.record_signal(
            symbol="000660",  # SK하이닉스
            signal_type="sell",
            condition_id=2,
            condition_value="MA > 100000",
            current_price=100000.0
        )
        
        self.signal_monitor.update_signal_execution(
            signal_id=signal_id2,
            executed_price=99000.0,
            executed_quantity=5
        )
        
        success = self.signal_monitor.close_signal(signal_id2, -5000.0)
        self.assertTrue(success)
        
        signals = self.signal_monitor.get_signals()
        failed_signal = [s for s in signals if s.id == signal_id2][0]
        self.assertEqual(failed_signal.status, SignalStatus.FAILED)
        self.assertEqual(failed_signal.profit_loss, -5000.0)
    
    def test_get_signals_with_filters(self):
        """필터링된 신호 조회 테스트"""
        # 여러 신호 기록
        self.signal_monitor.record_signal("005930", "buy", 1, "RSI < 30", 70000.0)
        self.signal_monitor.record_signal("000660", "sell", 2, "MA > 100000", 100000.0)
        self.signal_monitor.record_signal("005930", "buy", 1, "RSI < 25", 68000.0)
        
        # 종목별 필터링
        samsung_signals = self.signal_monitor.get_signals(symbol="005930")
        self.assertEqual(len(samsung_signals), 2)
        
        # 상태별 필터링
        pending_signals = self.signal_monitor.get_signals(status=SignalStatus.PENDING)
        self.assertEqual(len(pending_signals), 3)
        
        # 일수 필터링
        recent_signals = self.signal_monitor.get_signals(days=1)
        self.assertEqual(len(recent_signals), 3)
    
    def test_get_signal_statistics(self):
        """신호 통계 조회 테스트"""
        # 여러 신호 기록 (성공/실패 포함)
        signal_id1 = self.signal_monitor.record_signal("005930", "buy", 1, "RSI < 30", 70000.0)
        signal_id2 = self.signal_monitor.record_signal("000660", "sell", 2, "MA > 100000", 100000.0)
        signal_id3 = self.signal_monitor.record_signal("005380", "buy", 3, "Volume > 1000000", 50000.0)
        
        # 실행 및 종료
        self.signal_monitor.update_signal_execution(signal_id1, 70500.0, 10)
        self.signal_monitor.update_signal_execution(signal_id2, 99000.0, 5)
        self.signal_monitor.update_signal_execution(signal_id3, 51000.0, 20)
        
        self.signal_monitor.close_signal(signal_id1, 50000.0)  # 성공
        self.signal_monitor.close_signal(signal_id2, -5000.0)  # 실패
        self.signal_monitor.close_signal(signal_id3, 20000.0)  # 성공
        
        # 통계 조회
        stats = self.signal_monitor.get_signal_statistics()
        
        self.assertEqual(stats['total_signals'], 3)
        self.assertEqual(stats['executed_signals'], 3)
        self.assertEqual(stats['successful_signals'], 2)
        self.assertEqual(stats['success_rate'], 66.67)
        self.assertEqual(stats['total_profit_loss'], 65000.0)  # 50000 + (-5000) + 20000
    
    def test_get_recent_signals(self):
        """최근 신호 조회 테스트"""
        # 여러 신호 기록
        self.signal_monitor.record_signal("005930", "buy", 1, "RSI < 30", 70000.0)
        self.signal_monitor.record_signal("000660", "sell", 2, "MA > 100000", 100000.0)
        self.signal_monitor.record_signal("005380", "buy", 3, "Volume > 1000000", 50000.0)
        
        # 최근 2개만 조회
        recent_signals = self.signal_monitor.get_recent_signals(limit=2)
        self.assertEqual(len(recent_signals), 2)
        
        # 최신 신호가 먼저 나오는지 확인
        self.assertEqual(recent_signals[0].symbol, "005380")
        self.assertEqual(recent_signals[1].symbol, "000660")
    
    def test_get_pending_signals(self):
        """대기 중인 신호 조회 테스트"""
        # 여러 신호 기록
        signal_id1 = self.signal_monitor.record_signal("005930", "buy", 1, "RSI < 30", 70000.0)
        signal_id2 = self.signal_monitor.record_signal("000660", "sell", 2, "MA > 100000", 100000.0)
        
        # 하나만 실행
        self.signal_monitor.update_signal_execution(signal_id1, 70500.0, 10)
        
        # 대기 중인 신호 조회
        pending_signals = self.signal_monitor.get_pending_signals()
        self.assertEqual(len(pending_signals), 1)
        self.assertEqual(pending_signals[0].symbol, "000660")
    
    def test_signal_record_to_dict(self):
        """SignalRecord to_dict 메서드 테스트"""
        record = SignalRecord(
            id=1,
            symbol="005930",
            signal_type="buy",
            condition_id=1,
            condition_value="RSI < 30",
            current_price=70000.0,
            status=SignalStatus.PENDING,
            executed_price=None,
            executed_quantity=None,
            profit_loss=None,
            created_at=datetime.now(),
            executed_at=None,
            closed_at=None
        )
        
        data = record.to_dict()
        
        self.assertEqual(data['id'], 1)
        self.assertEqual(data['symbol'], "005930")
        self.assertEqual(data['signal_type'], "buy")
        self.assertEqual(data['status'], "pending")
        self.assertIsNone(data['executed_price'])
        self.assertIsNone(data['profit_loss'])

if __name__ == '__main__':
    unittest.main() 