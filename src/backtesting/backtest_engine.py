"""
백테스팅 엔진
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from src.core.logger import logger
from src.core.config import Config
from src.trading.trading_strategy import TradingStrategy
from src.trading.risk_manager import RiskManager
from src.core.data_collector import DataCollector

@dataclass
class Trade:
    """거래 정보"""
    timestamp: datetime
    symbol: str
    action: str  # 'BUY' or 'SELL'
    quantity: int
    price: float
    commission: float = 0.0
    reason: str = ""
    
@dataclass
class Position:
    """포지션 정보"""
    symbol: str
    quantity: int
    avg_price: float
    entry_time: datetime
    
@dataclass
class BacktestResult:
    """백테스트 결과"""
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    max_drawdown: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    avg_trade_return: float
    trades: List[Trade]
    equity_curve: pd.DataFrame
    positions: List[Position]
    
class BacktestEngine:
    def __init__(self, initial_capital: float = 10000000):
        """
        백테스팅 엔진 초기화
        
        Args:
            initial_capital: 초기 자본금
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.equity_curve: List[Dict] = []
        
        # 전략 및 리스크 관리
        self.strategy = TradingStrategy()
        self.risk_manager = RiskManager()
        self.data_collector = DataCollector()
        
        # 백테스트 설정
        self.commission_rate = 0.00015  # 수수료율 (0.015%)
        self.slippage_rate = 0.0001     # 슬리피지 (0.01%)
        
    def run_backtest(self, 
                    data: pd.DataFrame, 
                    symbol: str,
                    start_date: Optional[str] = None,
                    end_date: Optional[str] = None) -> BacktestResult:
        """
        백테스트 실행
        
        Args:
            data: OHLCV 데이터
            symbol: 종목 코드
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)
            
        Returns:
            BacktestResult: 백테스트 결과
        """
        try:
            logger.info(f"백테스트 시작: {symbol}")
            logger.info(f"초기 자본: {self.initial_capital:,}원")
            logger.info(f"데이터 기간: {data.index[0]} ~ {data.index[-1]}")
            
            # 데이터 필터링
            if start_date:
                data = data[data.index >= start_date]
            if end_date:
                data = data[data.index <= end_date]
            
            # 기술적 지표 계산
            data_with_indicators = self.data_collector.calculate_technical_indicators(data)
            
            # 백테스트 실행
            for i in range(len(data_with_indicators)):
                current_data = data_with_indicators.iloc[:i+1]
                current_row = data_with_indicators.iloc[i]
                current_time = current_data.index[i]
                
                # 매매 신호 생성
                signal = self._generate_signal(current_data, symbol)
                
                # 거래 실행
                if signal:
                    self._execute_trade(signal, current_time, current_row)
                
                # 포지션 업데이트
                self._update_positions(current_row, current_time)
                
                # 자본금 업데이트
                self._update_equity(current_row, current_time)
            
            # 결과 계산
            result = self._calculate_results(data_with_indicators)
            
            logger.info(f"백테스트 완료: 총 수익률 {result.total_return:.2f}%")
            return result
            
        except Exception as e:
            logger.error(f"백테스트 실행 중 오류: {e}")
            raise
    
    def _generate_signal(self, data: pd.DataFrame, symbol: str) -> Optional[Dict]:
        """
        매매 신호 생성
        """
        try:
            if len(data) < 20:  # 최소 데이터 포인트 확인
                return None
            
            # 현재 포지션 확인
            current_position = self.positions.get(symbol)
            
            # 전략 신호 생성
            signal = self.strategy.sma_crossover_strategy(data)
            
            if signal:
                # 리스크 관리 적용
                if signal['action'] == 'BUY' and not current_position:
                    # 매수 가능 자본 확인
                    if self.current_capital < 100000:  # 최소 거래 금액
                        return None
                    
                    # 포지션 크기 계산
                    quantity, position_size = self.risk_manager.calculate_position_size(
                        signal['price'], self.current_capital
                    )
                    
                    if quantity > 0:
                        signal['quantity'] = quantity
                        signal['position_size'] = position_size
                        return signal
                        
                elif signal['action'] == 'SELL' and current_position:
                    signal['quantity'] = current_position.quantity
                    return signal
            
            return None
            
        except Exception as e:
            logger.error(f"신호 생성 중 오류: {e}")
            return None
    
    def _execute_trade(self, signal: Dict, timestamp: datetime, current_row: pd.Series):
        """
        거래 실행
        """
        try:
            action = signal['action']
            quantity = signal['quantity']
            price = signal['price']
            
            # 수수료 및 슬리피지 적용
            commission = price * quantity * self.commission_rate
            slippage = price * quantity * self.slippage_rate
            total_cost = price * quantity + commission + slippage
            
            if action == 'BUY':
                # 매수 실행
                if self.current_capital >= total_cost:
                    # 포지션 생성/업데이트
                    if signal['symbol'] in self.positions:
                        # 기존 포지션에 추가
                        existing_pos = self.positions[signal['symbol']]
                        total_quantity = existing_pos.quantity + quantity
                        total_cost_before = existing_pos.avg_price * existing_pos.quantity
                        total_cost_after = total_cost_before + total_cost
                        new_avg_price = total_cost_after / total_quantity
                        
                        self.positions[signal['symbol']] = Position(
                            symbol=signal['symbol'],
                            quantity=total_quantity,
                            avg_price=new_avg_price,
                            entry_time=existing_pos.entry_time
                        )
                    else:
                        # 새 포지션 생성
                        self.positions[signal['symbol']] = Position(
                            symbol=signal['symbol'],
                            quantity=quantity,
                            avg_price=price,
                            entry_time=timestamp
                        )
                    
                    # 자본금 차감
                    self.current_capital -= total_cost
                    
                    # 거래 기록
                    trade = Trade(
                        timestamp=timestamp,
                        symbol=signal['symbol'],
                        action='BUY',
                        quantity=quantity,
                        price=price,
                        commission=commission,
                        reason=signal.get('reason', '매수 신호')
                    )
                    self.trades.append(trade)
                    
                    logger.info(f"매수 실행: {signal['symbol']} {quantity}주 @ {price:,}원")
                    
            elif action == 'SELL':
                # 매도 실행
                if signal['symbol'] in self.positions:
                    position = self.positions[signal['symbol']]
                    
                    # 수익/손실 계산
                    gross_profit = (price - position.avg_price) * quantity
                    net_profit = gross_profit - commission - slippage
                    
                    # 자본금 증가
                    self.current_capital += (price * quantity - commission - slippage)
                    
                    # 포지션 제거
                    del self.positions[signal['symbol']]
                    
                    # 거래 기록
                    trade = Trade(
                        timestamp=timestamp,
                        symbol=signal['symbol'],
                        action='SELL',
                        quantity=quantity,
                        price=price,
                        commission=commission,
                        reason=signal.get('reason', '매도 신호')
                    )
                    self.trades.append(trade)
                    
                    logger.info(f"매도 실행: {signal['symbol']} {quantity}주 @ {price:,}원 (손익: {net_profit:,.0f}원)")
                    
        except Exception as e:
            logger.error(f"거래 실행 중 오류: {e}")
    
    def _update_positions(self, current_row: pd.Series, timestamp: datetime):
        """
        포지션 업데이트 (손절/익절 확인)
        """
        try:
            current_price = current_row['종가']
            
            for symbol, position in list(self.positions.items()):
                # 손절 확인
                stop_loss_price = position.avg_price * (1 - Config.STOP_LOSS_PERCENT / 100)
                if current_price <= stop_loss_price:
                    signal = {
                        'action': 'SELL',
                        'symbol': symbol,
                        'quantity': position.quantity,
                        'price': current_price,
                        'reason': '손절'
                    }
                    self._execute_trade(signal, timestamp, current_row)
                
                # 익절 확인
                take_profit_price = position.avg_price * (1 + Config.TAKE_PROFIT_PERCENT / 100)
                if current_price >= take_profit_price:
                    signal = {
                        'action': 'SELL',
                        'symbol': symbol,
                        'quantity': position.quantity,
                        'price': current_price,
                        'reason': '익절'
                    }
                    self._execute_trade(signal, timestamp, current_row)
                    
        except Exception as e:
            logger.error(f"포지션 업데이트 중 오류: {e}")
    
    def _update_equity(self, current_row: pd.Series, timestamp: datetime):
        """
        자본금 업데이트
        """
        try:
            # 현재 포지션 가치 계산
            position_value = 0
            for symbol, position in self.positions.items():
                position_value += position.quantity * current_row['종가']
            
            # 총 자본금
            total_equity = self.current_capital + position_value
            
            # 자본금 곡선 기록
            self.equity_curve.append({
                'timestamp': timestamp,
                'cash': self.current_capital,
                'position_value': position_value,
                'total_equity': total_equity,
                'return': (total_equity - self.initial_capital) / self.initial_capital * 100
            })
            
        except Exception as e:
            logger.error(f"자본금 업데이트 중 오류: {e}")
    
    def _calculate_results(self, data: pd.DataFrame) -> BacktestResult:
        """
        백테스트 결과 계산
        """
        try:
            equity_df = pd.DataFrame(self.equity_curve)
            
            # 기본 지표 계산
            final_equity = equity_df['total_equity'].iloc[-1] if len(equity_df) > 0 else self.initial_capital
            total_return = (final_equity - self.initial_capital) / self.initial_capital * 100
            
            # 연간 수익률 계산
            if len(equity_df) > 1:
                start_date = equity_df['timestamp'].iloc[0]
                end_date = equity_df['timestamp'].iloc[-1]
                days = (end_date - start_date).days
                if days > 0:
                    annualized_return = ((final_equity / self.initial_capital) ** (365 / days) - 1) * 100
                else:
                    annualized_return = total_return
            else:
                annualized_return = total_return
            
            # 샤프 비율 계산
            if len(equity_df) > 1:
                returns = equity_df['total_equity'].pct_change().dropna()
                if len(returns) > 0 and returns.std() > 0:
                    sharpe_ratio = (returns.mean() * 252) / (returns.std() * np.sqrt(252))
                else:
                    sharpe_ratio = 0
            else:
                sharpe_ratio = 0
            
            # 최대 낙폭 계산
            if len(equity_df) > 0:
                equity_df['cummax'] = equity_df['total_equity'].cummax()
                equity_df['drawdown'] = (equity_df['total_equity'] - equity_df['cummax']) / equity_df['cummax'] * 100
                max_drawdown = equity_df['drawdown'].min()
            else:
                max_drawdown = 0
            
            # 거래 통계
            total_trades = len(self.trades)
            winning_trades = len([t for t in self.trades if t.action == 'SELL'])
            losing_trades = 0  # 실제 손익 계산 필요
            
            # 승률 계산
            if total_trades > 0:
                win_rate = winning_trades / total_trades * 100
            else:
                win_rate = 0
            
            # 수익 팩터 계산
            gross_profit = sum([t.price * t.quantity for t in self.trades if t.action == 'SELL'])
            gross_loss = sum([t.price * t.quantity for t in self.trades if t.action == 'BUY'])
            
            if gross_loss > 0:
                profit_factor = gross_profit / gross_loss
            else:
                profit_factor = float('inf') if gross_profit > 0 else 0
            
            # 평균 거래 수익률
            if total_trades > 0:
                avg_trade_return = total_return / total_trades
            else:
                avg_trade_return = 0
            
            return BacktestResult(
                total_return=total_return,
                annualized_return=annualized_return,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=win_rate,
                profit_factor=profit_factor,
                avg_trade_return=avg_trade_return,
                trades=self.trades,
                equity_curve=equity_df,
                positions=list(self.positions.values())
            )
            
        except Exception as e:
            logger.error(f"결과 계산 중 오류: {e}")
            raise 