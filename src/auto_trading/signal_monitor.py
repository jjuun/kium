"""
신호 모니터링 시스템
"""
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
from src.core.logger import logger

class SignalStatus(Enum):
    """신호 상태"""
    PENDING = "pending"      # 대기 중
    EXECUTED = "executed"    # 실행됨
    SUCCESS = "success"      # 성공
    FAILED = "failed"        # 실패
    CANCELLED = "cancelled"  # 취소됨

@dataclass
class SignalRecord:
    """신호 기록"""
    id: Optional[int]
    symbol: str
    signal_type: str  # 'buy' or 'sell'
    condition_id: int
    condition_value: str
    current_price: float
    rsi_value: Optional[float]
    status: SignalStatus
    executed_price: Optional[float]
    executed_quantity: Optional[int]
    profit_loss: Optional[float]
    created_at: datetime
    executed_at: Optional[datetime]
    closed_at: Optional[datetime]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'symbol': self.symbol,
            'signal_type': self.signal_type,
            'condition_id': self.condition_id,
            'condition_value': self.condition_value,
            'current_price': self.current_price,
            'rsi_value': self.rsi_value,
            'status': self.status.value,
            'executed_price': self.executed_price,
            'executed_quantity': self.executed_quantity,
            'profit_loss': self.profit_loss,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None
        }

class SignalMonitor:
    """신호 모니터링 클래스"""
    
    def __init__(self, db_path: str = "auto_trading.db"):
        """
        초기화
        
        Args:
            db_path: 데이터베이스 파일 경로
        """
        self.db_path = db_path
        self._init_database()
        
    def _init_database(self):
        """데이터베이스 초기화"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 신호 기록 테이블 생성
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS signal_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        signal_type TEXT NOT NULL,
                        condition_id INTEGER NOT NULL,
                        condition_value TEXT NOT NULL,
                        current_price REAL NOT NULL,
                        rsi_value REAL,
                        status TEXT NOT NULL DEFAULT 'pending',
                        executed_price REAL,
                        executed_quantity INTEGER,
                        profit_loss REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        executed_at TIMESTAMP,
                        closed_at TIMESTAMP
                    )
                """)
                
                # 인덱스 생성
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_signal_symbol_status
                    ON signal_history(symbol, status)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_signal_created_at
                    ON signal_history(created_at)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_signal_condition_id
                    ON signal_history(condition_id)
                """)
                
                conn.commit()
                logger.info("신호 모니터링 데이터베이스 초기화 완료")
                
        except Exception as e:
            logger.error(f"신호 모니터링 데이터베이스 초기화 실패: {e}")
            raise
    
    def record_signal(self, symbol: str, signal_type: str, condition_id: int, 
                     condition_value: str, current_price: float, rsi_value: float = None) -> int:
        """
        신호 기록
        
        Args:
            symbol: 종목코드
            signal_type: 신호 타입 ('buy' or 'sell')
            condition_id: 조건 ID
            condition_value: 조건 값
            current_price: 현재가
            rsi_value: RSI 값
            
        Returns:
            int: 신호 ID
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO signal_history 
                    (symbol, signal_type, condition_id, condition_value, current_price, rsi_value, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (symbol, signal_type, condition_id, condition_value, current_price, rsi_value,
                     SignalStatus.PENDING.value, datetime.now()))
                
                signal_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"신호 기록 완료: {symbol} {signal_type} (ID: {signal_id})")
                return signal_id
                
        except Exception as e:
            logger.error(f"신호 기록 실패: {e}")
            return -1
    
    def update_signal_execution(self, signal_id: int, executed_price: float, 
                               executed_quantity: int) -> bool:
        """
        신호 실행 정보 업데이트
        
        Args:
            signal_id: 신호 ID
            executed_price: 체결가
            executed_quantity: 체결수량
            
        Returns:
            bool: 업데이트 성공 여부
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE signal_history 
                    SET status = ?, executed_price = ?, executed_quantity = ?, executed_at = ?
                    WHERE id = ?
                """, (SignalStatus.EXECUTED.value, executed_price, executed_quantity, 
                     datetime.now(), signal_id))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(f"신호 실행 정보 업데이트 완료: {signal_id}")
                    return True
                else:
                    logger.warning(f"신호 실행 정보 업데이트 실패: {signal_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"신호 실행 정보 업데이트 실패: {e}")
            return False
    
    def close_signal(self, signal_id: int, profit_loss: float) -> bool:
        """
        신호 종료 (수익/손실 계산)
        
        Args:
            signal_id: 신호 ID
            profit_loss: 수익/손실
            
        Returns:
            bool: 종료 성공 여부
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                status = SignalStatus.SUCCESS.value if profit_loss > 0 else SignalStatus.FAILED.value
                
                cursor.execute("""
                    UPDATE signal_history 
                    SET status = ?, profit_loss = ?, closed_at = ?
                    WHERE id = ?
                """, (status, profit_loss, datetime.now(), signal_id))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(f"신호 종료 완료: {signal_id} (수익: {profit_loss})")
                    return True
                else:
                    logger.warning(f"신호 종료 실패: {signal_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"신호 종료 실패: {e}")
            return False
    
    def get_signals(self, symbol: str = None, status: SignalStatus = None, 
                   days: int = 30) -> List[SignalRecord]:
        """
        신호 목록 조회
        
        Args:
            symbol: 종목코드 (선택사항)
            status: 신호 상태 (선택사항)
            days: 조회 일수
            
        Returns:
            List[SignalRecord]: 신호 목록
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT id, symbol, signal_type, condition_id, condition_value, 
                           current_price, rsi_value, status, executed_price, executed_quantity, 
                           profit_loss, created_at, executed_at, closed_at
                    FROM signal_history 
                    WHERE created_at >= datetime('now', '-{} days')
                """.format(days)
                
                params = []
                if symbol:
                    query += " AND symbol = ?"
                    params.append(symbol)
                
                if status:
                    query += " AND status = ?"
                    params.append(status.value)
                
                query += " ORDER BY created_at DESC"
                
                cursor.execute(query, params)
                
                signals = []
                for row in cursor.fetchall():
                    signals.append(SignalRecord(
                        id=row[0],
                        symbol=row[1],
                        signal_type=row[2],
                        condition_id=row[3],
                        condition_value=row[4],
                        current_price=row[5],
                        rsi_value=row[6],
                        status=SignalStatus(row[7]),
                        executed_price=row[8],
                        executed_quantity=row[9],
                        profit_loss=row[10],
                        created_at=datetime.fromisoformat(row[11]) if row[11] else None,
                        executed_at=datetime.fromisoformat(row[12]) if row[12] else None,
                        closed_at=datetime.fromisoformat(row[13]) if row[13] else None
                    ))
                
                return signals
                
        except Exception as e:
            logger.error(f"신호 목록 조회 실패: {e}")
            return []
    
    def get_signal_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        신호 통계 정보 조회
        
        Args:
            days: 조회 일수
            
        Returns:
            Dict[str, Any]: 통계 정보
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 전체 신호 수
                cursor.execute("""
                    SELECT COUNT(*) FROM signal_history 
                    WHERE created_at >= datetime('now', '-{} days')
                """.format(days))
                total_signals = cursor.fetchone()[0]
                
                # 실행된 신호 수
                cursor.execute("""
                    SELECT COUNT(*) FROM signal_history 
                    WHERE status IN (?, ?) AND created_at >= datetime('now', '-{} days')
                """.format(days), (SignalStatus.SUCCESS.value, SignalStatus.FAILED.value))
                executed_signals = cursor.fetchone()[0]
                
                # 성공한 신호 수
                cursor.execute("""
                    SELECT COUNT(*) FROM signal_history 
                    WHERE status = ? AND created_at >= datetime('now', '-{} days')
                """.format(days), (SignalStatus.SUCCESS.value,))
                successful_signals = cursor.fetchone()[0]
                
                # 총 수익/손실
                cursor.execute("""
                    SELECT COALESCE(SUM(profit_loss), 0) FROM signal_history 
                    WHERE status IN (?, ?) AND created_at >= datetime('now', '-{} days')
                """.format(days), (SignalStatus.SUCCESS.value, SignalStatus.FAILED.value))
                total_profit_loss = cursor.fetchone()[0] or 0
                
                # 종목별 신호 수
                cursor.execute("""
                    SELECT symbol, COUNT(*) FROM signal_history 
                    WHERE created_at >= datetime('now', '-{} days')
                    GROUP BY symbol ORDER BY COUNT(*) DESC LIMIT 10
                """.format(days))
                top_symbols = cursor.fetchall()
                
                # 성공률 계산
                success_rate = (successful_signals / executed_signals * 100) if executed_signals > 0 else 0
                
                return {
                    'total_signals': total_signals,
                    'executed_signals': executed_signals,
                    'successful_signals': successful_signals,
                    'success_rate': round(success_rate, 2),
                    'total_profit_loss': total_profit_loss,
                    'top_symbols': [{'symbol': s[0], 'count': s[1]} for s in top_symbols],
                    'days': days
                }
                
        except Exception as e:
            logger.error(f"신호 통계 조회 실패: {e}")
            return {
                'total_signals': 0,
                'executed_signals': 0,
                'successful_signals': 0,
                'success_rate': 0,
                'total_profit_loss': 0,
                'top_symbols': [],
                'days': days
            }
    
    def get_recent_signals(self, limit: int = 10) -> List[SignalRecord]:
        """
        최근 신호 조회
        
        Args:
            limit: 조회 개수
            
        Returns:
            List[SignalRecord]: 최근 신호 목록
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, symbol, signal_type, condition_id, condition_value, 
                           current_price, rsi_value, status, executed_price, executed_quantity, 
                           profit_loss, created_at, executed_at, closed_at
                    FROM signal_history 
                    ORDER BY created_at DESC LIMIT ?
                """, (limit,))
                
                signals = []
                for row in cursor.fetchall():
                    signals.append(SignalRecord(
                        id=row[0],
                        symbol=row[1],
                        signal_type=row[2],
                        condition_id=row[3],
                        condition_value=row[4],
                        current_price=row[5],
                        rsi_value=row[6],
                        status=SignalStatus(row[7]),
                        executed_price=row[8],
                        executed_quantity=row[9],
                        profit_loss=row[10],
                        created_at=datetime.fromisoformat(row[11]) if row[11] else None,
                        executed_at=datetime.fromisoformat(row[12]) if row[12] else None,
                        closed_at=datetime.fromisoformat(row[13]) if row[13] else None
                    ))
                
                return signals
                
        except Exception as e:
            logger.error(f"최근 신호 조회 실패: {e}")
            return []
    
    def get_pending_signals(self) -> List[SignalRecord]:
        """
        대기 중인 신호 조회
        
        Returns:
            List[SignalRecord]: 대기 중인 신호 목록
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, symbol, signal_type, condition_id, condition_value, 
                           current_price, rsi_value, status, executed_price, executed_quantity, 
                           profit_loss, created_at, executed_at, closed_at
                    FROM signal_history 
                    WHERE status = ? ORDER BY created_at DESC
                """, (SignalStatus.PENDING.value,))
                
                signals = []
                for row in cursor.fetchall():
                    signals.append(SignalRecord(
                        id=row[0],
                        symbol=row[1],
                        signal_type=row[2],
                        condition_id=row[3],
                        condition_value=row[4],
                        current_price=row[5],
                        rsi_value=row[6],
                        status=SignalStatus(row[7]),
                        executed_price=row[8],
                        executed_quantity=row[9],
                        profit_loss=row[10],
                        created_at=datetime.fromisoformat(row[11]) if row[11] else None,
                        executed_at=datetime.fromisoformat(row[12]) if row[12] else None,
                        closed_at=datetime.fromisoformat(row[13]) if row[13] else None
                    ))
                
                return signals
                
        except Exception as e:
            logger.error(f"대기 중인 신호 조회 실패: {e}")
            return []
    
    def get_executed_signals(self, days: int = 1) -> List[SignalRecord]:
        """
        실행된 신호 조회
        
        Args:
            days: 조회 일수
            
        Returns:
            List[SignalRecord]: 실행된 신호 목록
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, symbol, signal_type, condition_id, condition_value, 
                           current_price, rsi_value, status, executed_price, executed_quantity, 
                           profit_loss, created_at, executed_at, closed_at
                    FROM signal_history 
                    WHERE status IN (?, ?, ?) 
                    AND created_at >= datetime('now', '-{} days')
                    ORDER BY executed_at DESC
                """.format(days), (SignalStatus.EXECUTED.value, SignalStatus.SUCCESS.value, SignalStatus.FAILED.value))
                
                signals = []
                for row in cursor.fetchall():
                    signals.append(SignalRecord(
                        id=row[0],
                        symbol=row[1],
                        signal_type=row[2],
                        condition_id=row[3],
                        condition_value=row[4],
                        current_price=row[5],
                        rsi_value=row[6],
                        status=SignalStatus(row[7]),
                        executed_price=row[8],
                        executed_quantity=row[9],
                        profit_loss=row[10],
                        created_at=datetime.fromisoformat(row[11]) if row[11] else None,
                        executed_at=datetime.fromisoformat(row[12]) if row[12] else None,
                        closed_at=datetime.fromisoformat(row[13]) if row[13] else None
                    ))
                
                return signals
                
        except Exception as e:
            logger.error(f"실행된 신호 조회 실패: {e}")
            return [] 