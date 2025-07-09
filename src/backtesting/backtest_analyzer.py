"""
백테스트 결과 분석 및 시각화
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from typing import Dict, List, Any
from src.core.logger import logger
from src.backtesting.backtest_engine import BacktestResult

class BacktestAnalyzer:
    def __init__(self, result: BacktestResult):
        """
        백테스트 분석기 초기화
        
        Args:
            result: 백테스트 결과
        """
        self.result = result
        self.equity_curve = result.equity_curve
        self.trades = result.trades
        
        # 한글 폰트 설정
        plt.rcParams['font.family'] = 'DejaVu Sans'
        plt.rcParams['axes.unicode_minus'] = False
        
    def generate_summary_report(self) -> Dict[str, Any]:
        """
        백테스트 요약 보고서 생성
        """
        try:
            summary = {
                '기본 지표': {
                    '총 수익률 (%)': f"{self.result.total_return:.2f}",
                    '연간 수익률 (%)': f"{self.result.annualized_return:.2f}",
                    '샤프 비율': f"{self.result.sharpe_ratio:.3f}",
                    '최대 낙폭 (%)': f"{self.result.max_drawdown:.2f}",
                },
                '거래 통계': {
                    '총 거래 횟수': self.result.total_trades,
                    '승리 거래': self.result.winning_trades,
                    '패배 거래': self.result.losing_trades,
                    '승률 (%)': f"{self.result.win_rate:.1f}",
                    '수익 팩터': f"{self.result.profit_factor:.3f}",
                    '평균 거래 수익률 (%)': f"{self.result.avg_trade_return:.2f}",
                },
                '리스크 지표': {
                    '변동성 (%)': self._calculate_volatility(),
                    'VaR (95%)': self._calculate_var(),
                    'CVaR (95%)': self._calculate_cvar(),
                    '칼마 비율': self._calculate_calmar_ratio(),
                }
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"요약 보고서 생성 중 오류: {e}")
            return {}
    
    def plot_equity_curve(self, save_path: str = None):
        """
        자본금 곡선 플롯
        """
        try:
            if self.equity_curve.empty:
                logger.warning("자본금 곡선 데이터가 없습니다.")
                return
            
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
            
            # 자본금 곡선
            ax1.plot(self.equity_curve['timestamp'], self.equity_curve['total_equity'], 
                    label='총 자본금', linewidth=2)
            ax1.plot(self.equity_curve['timestamp'], self.equity_curve['cash'], 
                    label='현금', alpha=0.7)
            ax1.plot(self.equity_curve['timestamp'], self.equity_curve['position_value'], 
                    label='포지션 가치', alpha=0.7)
            
            ax1.set_title('자본금 곡선', fontsize=14, fontweight='bold')
            ax1.set_ylabel('자본금 (원)')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # 수익률 곡선
            ax2.plot(self.equity_curve['timestamp'], self.equity_curve['return'], 
                    label='수익률 (%)', color='green', linewidth=2)
            ax2.axhline(y=0, color='red', linestyle='--', alpha=0.5)
            
            ax2.set_title('수익률 곡선', fontsize=14, fontweight='bold')
            ax2.set_ylabel('수익률 (%)')
            ax2.set_xlabel('날짜')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"자본금 곡선 저장: {save_path}")
            
            plt.show()
            
        except Exception as e:
            logger.error(f"자본금 곡선 플롯 중 오류: {e}")
    
    def plot_drawdown(self, save_path: str = None):
        """
        낙폭 플롯
        """
        try:
            if self.equity_curve.empty:
                logger.warning("자본금 곡선 데이터가 없습니다.")
                return
            
            # 낙폭 계산
            equity_curve = self.equity_curve.copy()
            equity_curve['cummax'] = equity_curve['total_equity'].cummax()
            equity_curve['drawdown'] = (equity_curve['total_equity'] - equity_curve['cummax']) / equity_curve['cummax'] * 100
            
            plt.figure(figsize=(12, 6))
            plt.fill_between(equity_curve['timestamp'], equity_curve['drawdown'], 0, 
                           alpha=0.3, color='red', label='낙폭')
            plt.plot(equity_curve['timestamp'], equity_curve['drawdown'], 
                    color='red', linewidth=1)
            
            plt.title('낙폭 분석', fontsize=14, fontweight='bold')
            plt.ylabel('낙폭 (%)')
            plt.xlabel('날짜')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"낙폭 플롯 저장: {save_path}")
            
            plt.show()
            
        except Exception as e:
            logger.error(f"낙폭 플롯 중 오류: {e}")
    
    def plot_monthly_returns(self, save_path: str = None):
        """
        월별 수익률 히트맵
        """
        try:
            if self.equity_curve.empty:
                logger.warning("자본금 곡선 데이터가 없습니다.")
                return
            
            # 월별 수익률 계산
            equity_curve = self.equity_curve.copy()
            equity_curve['year'] = equity_curve['timestamp'].dt.year
            equity_curve['month'] = equity_curve['timestamp'].dt.month
            
            monthly_returns = equity_curve.groupby(['year', 'month'])['total_equity'].last().pct_change() * 100
            
            # 히트맵 데이터 준비
            monthly_returns_df = monthly_returns.unstack()
            
            plt.figure(figsize=(12, 8))
            sns.heatmap(monthly_returns_df, annot=True, fmt='.1f', cmap='RdYlGn', 
                       center=0, cbar_kws={'label': '수익률 (%)'})
            
            plt.title('월별 수익률 히트맵', fontsize=14, fontweight='bold')
            plt.xlabel('월')
            plt.ylabel('년도')
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"월별 수익률 히트맵 저장: {save_path}")
            
            plt.show()
            
        except Exception as e:
            logger.error(f"월별 수익률 히트맵 중 오류: {e}")
    
    def plot_trade_analysis(self, save_path: str = None):
        """
        거래 분석 플롯
        """
        try:
            if not self.trades:
                logger.warning("거래 데이터가 없습니다.")
                return
            
            # 거래 데이터 준비
            trades_df = pd.DataFrame([
                {
                    'timestamp': t.timestamp,
                    'action': t.action,
                    'price': t.price,
                    'quantity': t.quantity,
                    'value': t.price * t.quantity,
                    'commission': t.commission
                } for t in self.trades
            ])
            
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
            
            # 거래 시점별 가격
            buy_trades = trades_df[trades_df['action'] == 'BUY']
            sell_trades = trades_df[trades_df['action'] == 'SELL']
            
            ax1.scatter(buy_trades['timestamp'], buy_trades['price'], 
                       color='green', alpha=0.7, label='매수', s=50)
            ax1.scatter(sell_trades['timestamp'], sell_trades['price'], 
                       color='red', alpha=0.7, label='매도', s=50)
            ax1.set_title('거래 시점별 가격')
            ax1.set_ylabel('가격 (원)')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # 거래량 분포
            ax2.hist(trades_df['quantity'], bins=20, alpha=0.7, color='blue')
            ax2.set_title('거래량 분포')
            ax2.set_xlabel('거래량 (주)')
            ax2.set_ylabel('빈도')
            ax2.grid(True, alpha=0.3)
            
            # 거래 금액 분포
            ax3.hist(trades_df['value'], bins=20, alpha=0.7, color='orange')
            ax3.set_title('거래 금액 분포')
            ax3.set_xlabel('거래 금액 (원)')
            ax3.set_ylabel('빈도')
            ax3.grid(True, alpha=0.3)
            
            # 거래 시점 분포
            trades_df['hour'] = trades_df['timestamp'].dt.hour
            ax4.hist(trades_df['hour'], bins=24, alpha=0.7, color='purple')
            ax4.set_title('거래 시점 분포')
            ax4.set_xlabel('시간 (시)')
            ax4.set_ylabel('빈도')
            ax4.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"거래 분석 플롯 저장: {save_path}")
            
            plt.show()
            
        except Exception as e:
            logger.error(f"거래 분석 플롯 중 오류: {e}")
    
    def _calculate_volatility(self) -> float:
        """변동성 계산"""
        try:
            if len(self.equity_curve) > 1:
                returns = self.equity_curve['total_equity'].pct_change().dropna()
                return returns.std() * np.sqrt(252) * 100
            return 0.0
        except Exception as e:
            logger.error(f"변동성 계산 중 오류: {e}")
            return 0.0
    
    def _calculate_var(self, confidence_level: float = 0.95) -> float:
        """VaR (Value at Risk) 계산"""
        try:
            if len(self.equity_curve) > 1:
                returns = self.equity_curve['total_equity'].pct_change().dropna()
                var = np.percentile(returns, (1 - confidence_level) * 100)
                return var * 100
            return 0.0
        except Exception as e:
            logger.error(f"VaR 계산 중 오류: {e}")
            return 0.0
    
    def _calculate_cvar(self, confidence_level: float = 0.95) -> float:
        """CVaR (Conditional Value at Risk) 계산"""
        try:
            if len(self.equity_curve) > 1:
                returns = self.equity_curve['total_equity'].pct_change().dropna()
                var = np.percentile(returns, (1 - confidence_level) * 100)
                cvar = returns[returns <= var].mean()
                return cvar * 100
            return 0.0
        except Exception as e:
            logger.error(f"CVaR 계산 중 오류: {e}")
            return 0.0
    
    def _calculate_calmar_ratio(self) -> float:
        """칼마 비율 계산"""
        try:
            if self.result.max_drawdown != 0:
                return self.result.annualized_return / abs(self.result.max_drawdown)
            return 0.0
        except Exception as e:
            logger.error(f"칼마 비율 계산 중 오류: {e}")
            return 0.0
    
    def export_results(self, file_path: str):
        """
        백테스트 결과를 CSV 파일로 내보내기
        """
        try:
            # 자본금 곡선 내보내기
            equity_path = file_path.replace('.csv', '_equity.csv')
            self.equity_curve.to_csv(equity_path, index=False)
            
            # 거래 내역 내보내기
            trades_path = file_path.replace('.csv', '_trades.csv')
            trades_df = pd.DataFrame([
                {
                    'timestamp': t.timestamp,
                    'symbol': t.symbol,
                    'action': t.action,
                    'quantity': t.quantity,
                    'price': t.price,
                    'commission': t.commission,
                    'reason': t.reason
                } for t in self.trades
            ])
            trades_df.to_csv(trades_path, index=False)
            
            logger.info(f"백테스트 결과 내보내기 완료: {equity_path}, {trades_path}")
            
        except Exception as e:
            logger.error(f"결과 내보내기 중 오류: {e}") 