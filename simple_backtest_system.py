#!/usr/bin/env python3
"""
간단하고 안정적인 백테스트 시스템
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Optional
from src.core.logger import logger
from src.core.data_collector import DataCollector

@dataclass
class SimpleTrade:
    """간단한 거래 정보"""
    timestamp: datetime
    action: str  # 'BUY' or 'SELL'
    quantity: int
    price: float
    reason: str = ""

@dataclass
class SimpleBacktestResult:
    """간단한 백테스트 결과"""
    total_return: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    trades: List[SimpleTrade]
    equity_curve: List[float]

class SimpleBacktestEngine:
    """간단한 백테스트 엔진"""
    
    def __init__(self, initial_capital: float = 10000000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.position = 0  # 보유 주식 수
        self.avg_price = 0  # 평균 매수가
        self.trades: List[SimpleTrade] = []
        self.equity_curve: List[float] = []
        
    def run_backtest(self, data: pd.DataFrame, symbol: str) -> SimpleBacktestResult:
        """백테스트 실행"""
        logger.info(f"간단한 백테스트 시작: {symbol}")
        logger.info(f"초기 자본: {self.initial_capital:,}원")
        
        for i in range(len(data)):
            current_row = data.iloc[i]
            current_time = data.index[i]
            current_price = current_row['종가']
            
            # 매매 신호 생성
            signal = self._generate_signal(data.iloc[:i+1], current_row)
            
            # 거래 실행
            if signal:
                self._execute_trade(signal, current_time, current_price)
            
            # 자본금 업데이트
            self._update_equity(current_price, current_time)
        
        # 결과 계산
        return self._calculate_results()
    
    def _generate_signal(self, data: pd.DataFrame, current_row: pd.Series) -> Optional[Dict]:
        """매매 신호 생성 (간단한 RSI 전략)"""
        if len(data) < 20:
            return None
        
        current_rsi = current_row['RSI']
        
        # RSI 과매도 (매수 신호)
        if current_rsi < 30 and self.position == 0:
            return {
                'action': 'BUY',
                'reason': 'RSI 과매도'
            }
        
        # RSI 과매수 (매도 신호)
        elif current_rsi > 70 and self.position > 0:
            return {
                'action': 'SELL',
                'reason': 'RSI 과매수'
            }
        
        return None
    
    def _execute_trade(self, signal: Dict, timestamp: datetime, price: float):
        """거래 실행"""
        action = signal['action']
        reason = signal['reason']
        
        if action == 'BUY':
            # 매수 수량 계산 (전체 자본의 20% 사용)
            trade_amount = self.current_capital * 0.2
            quantity = int(trade_amount / price)
            
            if quantity > 0:
                # 포지션 업데이트
                if self.position == 0:
                    self.avg_price = price
                else:
                    # 평균 매수가 계산
                    total_cost = self.avg_price * self.position + price * quantity
                    self.avg_price = total_cost / (self.position + quantity)
                
                self.position += quantity
                self.current_capital -= price * quantity
                
                # 거래 기록
                trade = SimpleTrade(
                    timestamp=timestamp,
                    action='BUY',
                    quantity=quantity,
                    price=price,
                    reason=reason
                )
                self.trades.append(trade)
                
                logger.info(f"매수 실행: {quantity}주 @ {price:,}원 ({reason})")
        
        elif action == 'SELL':
            if self.position > 0:
                # 매도 실행
                sell_quantity = self.position
                profit = (price - self.avg_price) * sell_quantity
                
                self.current_capital += price * sell_quantity
                self.position = 0
                self.avg_price = 0
                
                # 거래 기록
                trade = SimpleTrade(
                    timestamp=timestamp,
                    action='SELL',
                    quantity=sell_quantity,
                    price=price,
                    reason=reason
                )
                self.trades.append(trade)
                
                logger.info(f"매도 실행: {sell_quantity}주 @ {price:,}원 (손익: {profit:,.0f}원, {reason})")
    
    def _update_equity(self, current_price: float, timestamp: datetime):
        """자본금 업데이트"""
        position_value = self.position * current_price
        total_equity = self.current_capital + position_value
        self.equity_curve.append(total_equity)
    
    def _calculate_results(self) -> SimpleBacktestResult:
        """결과 계산"""
        final_equity = self.equity_curve[-1] if self.equity_curve else self.initial_capital
        total_return = (final_equity - self.initial_capital) / self.initial_capital * 100
        
        # 거래 분석
        buy_trades = [t for t in self.trades if t.action == 'BUY']
        sell_trades = [t for t in self.trades if t.action == 'SELL']
        
        total_trades = len(sell_trades)  # 완료된 거래만 카운트
        winning_trades = 0
        losing_trades = 0
        
        # 승률 계산
        for i in range(min(len(buy_trades), len(sell_trades))):
            buy_price = buy_trades[i].price
            sell_price = sell_trades[i].price
            
            if sell_price > buy_price:
                winning_trades += 1
            else:
                losing_trades += 1
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        return SimpleBacktestResult(
            total_return=total_return,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            trades=self.trades,
            equity_curve=self.equity_curve
        )

def run_simple_backtest():
    """간단한 백테스트 실행"""
    print("🚀 간단한 백테스트 시스템 시작")
    print("="*60)
    
    try:
        # 데이터 수집기 초기화
        data_collector = DataCollector()
        
        # 삼성SDI 데이터 수집 (6개월치)
        print("📊 삼성SDI 데이터 수집 중...")
        data = data_collector.get_historical_data("006400", 180)
        
        if data is None or data.empty:
            print("❌ 데이터 수집 실패")
            return
        
        print(f"데이터 수집 완료: {len(data)}개 데이터")
        print(f"기간: {data.index[0].strftime('%Y-%m-%d')} ~ {data.index[-1].strftime('%Y-%m-%d')}")
        print(f"가격 범위: {data['종가'].min():,.0f}원 ~ {data['종가'].max():,.0f}원")
        
        # 기술적 지표 계산
        print("\n📈 기술적 지표 계산 중...")
        data_with_indicators = data_collector.calculate_technical_indicators(data)
        
        # 백테스트 엔진 초기화
        print("\n⚙️ 백테스트 엔진 초기화...")
        engine = SimpleBacktestEngine(initial_capital=10000000)
        
        # 백테스트 실행
        print("🔄 백테스트 실행 중...")
        result = engine.run_backtest(data_with_indicators, "006400")
        
        # 결과 출력
        print("\n📈 백테스트 결과:")
        print(f"총 수익률: {result.total_return:.2f}%")
        print(f"총 거래 횟수: {result.total_trades}")
        print(f"승리 거래: {result.winning_trades}")
        print(f"패배 거래: {result.losing_trades}")
        print(f"승률: {result.win_rate:.1f}%")
        
        # 거래 내역 요약
        if result.trades:
            print(f"\n💼 거래 내역 요약:")
            buy_trades = [t for t in result.trades if t.action == 'BUY']
            sell_trades = [t for t in result.trades if t.action == 'SELL']
            print(f"  매수 거래: {len(buy_trades)}회")
            print(f"  매도 거래: {len(sell_trades)}회")
            
            if sell_trades:
                avg_sell_price = sum(t.price for t in sell_trades) / len(sell_trades)
                print(f"  평균 매도가: {avg_sell_price:,.0f}원")
        
        print("\n✅ 간단한 백테스트 완료!")
        
    except Exception as e:
        print(f"\n❌ 백테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()

def run_comparative_backtest():
    """여러 종목 비교 백테스트 실행"""
    print("🚀 다중 종목 비교 백테스트 시스템 시작")
    print("="*80)
    
    # 테스트할 종목 리스트
    stocks = [
        ("005930", "삼성전자"),
        ("006400", "삼성SDI"),
        ("009150", "삼성전기"),
        ("096770", "SK이노베이션"),
        ("028300", "HLB"),
        ("005389", "현대차3우B"),
        ("066575", "LG전자우"),
        ("042700", "한미반도체")
    ]
    
    results = []
    
    for stock_code, stock_name in stocks:
        print(f"\n📊 {stock_name}({stock_code}) 백테스트 시작...")
        print("-" * 60)
        
        try:
            # 데이터 수집기 초기화
            data_collector = DataCollector()
            
            # 데이터 수집 (6개월치)
            print(f"📈 {stock_name} 데이터 수집 중...")
            data = data_collector.get_historical_data(stock_code, 180)
            
            if data is None or data.empty:
                print(f"❌ {stock_name} 데이터 수집 실패")
                continue
            
            print(f"데이터 수집 완료: {len(data)}개 데이터")
            print(f"기간: {data.index[0].strftime('%Y-%m-%d')} ~ {data.index[-1].strftime('%Y-%m-%d')}")
            print(f"가격 범위: {data['종가'].min():,.0f}원 ~ {data['종가'].max():,.0f}원")
            
            # 기술적 지표 계산
            print("📊 기술적 지표 계산 중...")
            data_with_indicators = data_collector.calculate_technical_indicators(data)
            
            # 백테스트 엔진 초기화
            print("⚙️ 백테스트 엔진 초기화...")
            engine = SimpleBacktestEngine(initial_capital=10000000)
            
            # 백테스트 실행
            print("🔄 백테스트 실행 중...")
            result = engine.run_backtest(data_with_indicators, stock_code)
            
            # 결과 저장
            result_data = {
                '종목코드': stock_code,
                '종목명': stock_name,
                '총수익률': result.total_return,
                '총거래횟수': result.total_trades,
                '승리거래': result.winning_trades,
                '패배거래': result.losing_trades,
                '승률': result.win_rate,
                '거래내역': result.trades
            }
            results.append(result_data)
            
            # 개별 결과 출력
            print(f"\n📈 {stock_name} 백테스트 결과:")
            print(f"  총 수익률: {result.total_return:.2f}%")
            print(f"  총 거래 횟수: {result.total_trades}회")
            print(f"  승리 거래: {result.winning_trades}회")
            print(f"  패배 거래: {result.losing_trades}회")
            print(f"  승률: {result.win_rate:.1f}%")
            
            # 거래 내역 요약
            if result.trades:
                buy_trades = [t for t in result.trades if t.action == 'BUY']
                sell_trades = [t for t in result.trades if t.action == 'SELL']
                print(f"  매수 거래: {len(buy_trades)}회")
                print(f"  매도 거래: {len(sell_trades)}회")
                
                if sell_trades:
                    avg_sell_price = sum(t.price for t in sell_trades) / len(sell_trades)
                    print(f"  평균 매도가: {avg_sell_price:,.0f}원")
            
        except Exception as e:
            print(f"❌ {stock_name} 백테스트 중 오류 발생: {str(e)}")
            continue
    
    # 종합 결과 출력
    print("\n" + "="*80)
    print("📊 종합 비교 결과")
    print("="*80)
    
    if results:
        # 결과를 총수익률 기준으로 정렬
        results.sort(key=lambda x: x['총수익률'], reverse=True)
        
        print(f"{'순위':<4} {'종목명':<12} {'종목코드':<8} {'총수익률':<8} {'거래횟수':<6} {'승률':<6} {'승리':<4} {'패배':<4}")
        print("-" * 70)
        
        for i, result in enumerate(results, 1):
            print(f"{i:<4} {result['종목명']:<12} {result['종목코드']:<8} "
                  f"{result['총수익률']:<8.2f}% {result['총거래횟수']:<6} "
                  f"{result['승률']:<6.1f}% {result['승리거래']:<4} {result['패배거래']:<4}")
        
        # 통계 요약
        print("\n📈 통계 요약:")
        total_return_avg = sum(r['총수익률'] for r in results) / len(results)
        win_rate_avg = sum(r['승률'] for r in results) / len(results)
        total_trades_avg = sum(r['총거래횟수'] for r in results) / len(results)
        
        print(f"  평균 총수익률: {total_return_avg:.2f}%")
        print(f"  평균 승률: {win_rate_avg:.1f}%")
        print(f"  평균 거래횟수: {total_trades_avg:.1f}회")
        
        # 최고 성과 종목
        best_stock = results[0]
        print(f"\n🏆 최고 성과 종목: {best_stock['종목명']}({best_stock['종목코드']})")
        print(f"  총수익률: {best_stock['총수익률']:.2f}%")
        print(f"  승률: {best_stock['승률']:.1f}%")
        print(f"  거래횟수: {best_stock['총거래횟수']}회")
        
        # 최저 성과 종목
        worst_stock = results[-1]
        print(f"\n📉 최저 성과 종목: {worst_stock['종목명']}({worst_stock['종목코드']})")
        print(f"  총수익률: {worst_stock['총수익률']:.2f}%")
        print(f"  승률: {worst_stock['승률']:.1f}%")
        print(f"  거래횟수: {worst_stock['총거래횟수']}회")
        
    else:
        print("❌ 성공적으로 완료된 백테스트가 없습니다.")

def main():
    """메인 함수"""
    run_simple_backtest()
    
    print("\n🎯 다음 단계 제안:")
    print("1. 더 다양한 전략 구현")
    print("2. 포트폴리오 백테스트 (여러 종목)")
    print("3. 전략 파라미터 최적화")
    print("4. 리스크 관리 시스템 추가")
    print("5. 실시간 거래 시스템과 연동")

if __name__ == "__main__":
    run_comparative_backtest() 