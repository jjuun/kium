"""
전략 최적화 모듈
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from itertools import product
from typing import Dict, List, Any, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed
from src.core.logger import logger
from src.backtesting.backtest_engine import BacktestEngine
from src.backtesting.backtest_analyzer import BacktestAnalyzer

class StrategyOptimizer:
    def __init__(self, data: pd.DataFrame, symbol: str, initial_capital: float = 10000000):
        """
        전략 최적화기 초기화
        
        Args:
            data: OHLCV 데이터
            symbol: 종목 코드
            initial_capital: 초기 자본금
        """
        self.data = data
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.results = []
        
    def optimize_sma_crossover(self, 
                             short_periods: List[int] = None,
                             long_periods: List[int] = None,
                             stop_loss_range: List[float] = None,
                             take_profit_range: List[float] = None,
                             max_workers: int = 4) -> pd.DataFrame:
        """
        SMA 교차 전략 최적화
        
        Args:
            short_periods: 단기 이동평균 기간 리스트
            long_periods: 장기 이동평균 기간 리스트
            stop_loss_range: 손절 비율 리스트
            take_profit_range: 익절 비율 리스트
            max_workers: 병렬 처리 워커 수
            
        Returns:
            최적화 결과 DataFrame
        """
        try:
            # 기본값 설정
            if short_periods is None:
                short_periods = [3, 5, 8, 10, 12, 15]
            if long_periods is None:
                long_periods = [15, 20, 25, 30, 35, 40]
            if stop_loss_range is None:
                stop_loss_range = [1.0, 2.0, 3.0, 5.0]
            if take_profit_range is None:
                take_profit_range = [3.0, 5.0, 7.0, 10.0]
            
            logger.info(f"SMA 교차 전략 최적화 시작")
            logger.info(f"단기 기간: {short_periods}")
            logger.info(f"장기 기간: {long_periods}")
            logger.info(f"손절 비율: {stop_loss_range}")
            logger.info(f"익절 비율: {take_profit_range}")
            
            # 파라미터 조합 생성
            param_combinations = list(product(short_periods, long_periods, stop_loss_range, take_profit_range))
            
            # 유효한 조합만 필터링 (단기 < 장기)
            valid_combinations = [(s, l, sl, tp) for s, l, sl, tp in param_combinations if s < l]
            
            logger.info(f"총 {len(valid_combinations)}개의 파라미터 조합으로 최적화 진행")
            
            # 병렬 처리로 백테스트 실행
            results = []
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                # 작업 제출
                future_to_params = {
                    executor.submit(self._run_single_backtest, params): params 
                    for params in valid_combinations
                }
                
                # 결과 수집
                for future in as_completed(future_to_params):
                    params = future_to_params[future]
                    try:
                        result = future.result()
                        if result:
                            results.append(result)
                            logger.info(f"완료: {params} -> 수익률: {result['total_return']:.2f}%")
                    except Exception as e:
                        logger.error(f"파라미터 {params} 백테스트 실패: {e}")
            
            # 결과를 DataFrame으로 변환
            results_df = pd.DataFrame(results)
            
            if not results_df.empty:
                # 결과 정렬 (수익률 기준)
                results_df = results_df.sort_values('total_return', ascending=False)
                
                logger.info(f"최적화 완료: 최고 수익률 {results_df['total_return'].iloc[0]:.2f}%")
                logger.info(f"최적 파라미터: {results_df.iloc[0].to_dict()}")
            
            return results_df
            
        except Exception as e:
            logger.error(f"SMA 교차 전략 최적화 중 오류: {e}")
            return pd.DataFrame()
    
    def _run_single_backtest(self, params: Tuple) -> Dict[str, Any]:
        """
        단일 백테스트 실행
        
        Args:
            params: (short_period, long_period, stop_loss, take_profit)
            
        Returns:
            백테스트 결과 딕셔너리
        """
        try:
            short_period, long_period, stop_loss, take_profit = params
            
            # 백테스트 엔진 생성
            engine = BacktestEngine(self.initial_capital)
            
            # 설정 임시 변경
            from src.core.config import Config
            original_short = Config.SHORT_PERIOD
            original_long = Config.LONG_PERIOD
            original_stop_loss = Config.STOP_LOSS_PERCENT
            original_take_profit = Config.TAKE_PROFIT_PERCENT
            
            Config.SHORT_PERIOD = short_period
            Config.LONG_PERIOD = long_period
            Config.STOP_LOSS_PERCENT = stop_loss
            Config.TAKE_PROFIT_PERCENT = take_profit
            
            # 백테스트 실행
            result = engine.run_backtest(self.data, self.symbol)
            
            # 설정 복원
            Config.SHORT_PERIOD = original_short
            Config.LONG_PERIOD = original_long
            Config.STOP_LOSS_PERCENT = original_stop_loss
            Config.TAKE_PROFIT_PERCENT = original_take_profit
            
            # 결과 반환
            return {
                'short_period': short_period,
                'long_period': long_period,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'total_return': result.total_return,
                'annualized_return': result.annualized_return,
                'sharpe_ratio': result.sharpe_ratio,
                'max_drawdown': result.max_drawdown,
                'total_trades': result.total_trades,
                'win_rate': result.win_rate,
                'profit_factor': result.profit_factor
            }
            
        except Exception as e:
            logger.error(f"단일 백테스트 실행 중 오류: {e}")
            return None
    
    def optimize_risk_parameters(self, 
                               position_size_range: List[float] = None,
                               commission_range: List[float] = None,
                               slippage_range: List[float] = None) -> pd.DataFrame:
        """
        리스크 파라미터 최적화
        
        Args:
            position_size_range: 포지션 크기 비율 리스트
            commission_range: 수수료율 리스트
            slippage_range: 슬리피지율 리스트
            
        Returns:
            최적화 결과 DataFrame
        """
        try:
            # 기본값 설정
            if position_size_range is None:
                position_size_range = [0.05, 0.1, 0.15, 0.2, 0.25]
            if commission_range is None:
                commission_range = [0.0001, 0.00015, 0.0002, 0.00025]
            if slippage_range is None:
                slippage_range = [0.00005, 0.0001, 0.00015, 0.0002]
            
            logger.info(f"리스크 파라미터 최적화 시작")
            
            # 파라미터 조합 생성
            param_combinations = list(product(position_size_range, commission_range, slippage_range))
            
            results = []
            for params in param_combinations:
                try:
                    result = self._run_risk_backtest(params)
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.error(f"리스크 파라미터 {params} 백테스트 실패: {e}")
            
            results_df = pd.DataFrame(results)
            
            if not results_df.empty:
                results_df = results_df.sort_values('sharpe_ratio', ascending=False)
                logger.info(f"리스크 최적화 완료: 최고 샤프 비율 {results_df['sharpe_ratio'].iloc[0]:.3f}")
            
            return results_df
            
        except Exception as e:
            logger.error(f"리스크 파라미터 최적화 중 오류: {e}")
            return pd.DataFrame()
    
    def _run_risk_backtest(self, params: Tuple) -> Dict[str, Any]:
        """
        리스크 파라미터 백테스트 실행
        """
        try:
            position_size, commission, slippage = params
            
            # 백테스트 엔진 생성
            engine = BacktestEngine(self.initial_capital)
            engine.commission_rate = commission
            engine.slippage_rate = slippage
            
            # 포지션 크기 계산 함수 수정
            def custom_position_size(current_price, available_capital):
                position_size_amount = available_capital * position_size
                quantity = int(position_size_amount / current_price)
                if quantity < 1:
                    quantity = 1
                return quantity, quantity * current_price
            
            # 백테스트 실행
            result = engine.run_backtest(self.data, self.symbol)
            
            return {
                'position_size': position_size,
                'commission': commission,
                'slippage': slippage,
                'total_return': result.total_return,
                'sharpe_ratio': result.sharpe_ratio,
                'max_drawdown': result.max_drawdown,
                'total_trades': result.total_trades,
                'win_rate': result.win_rate
            }
            
        except Exception as e:
            logger.error(f"리스크 백테스트 실행 중 오류: {e}")
            return None
    
    def grid_search(self, 
                   param_grid: Dict[str, List[Any]],
                   metric: str = 'total_return',
                   max_workers: int = 4) -> pd.DataFrame:
        """
        그리드 서치를 통한 전략 최적화
        
        Args:
            param_grid: 파라미터 그리드 딕셔너리
            metric: 최적화 기준 지표
            max_workers: 병렬 처리 워커 수
            
        Returns:
            최적화 결과 DataFrame
        """
        try:
            logger.info(f"그리드 서치 최적화 시작")
            logger.info(f"파라미터 그리드: {param_grid}")
            logger.info(f"최적화 지표: {metric}")
            
            # 파라미터 조합 생성
            param_names = list(param_grid.keys())
            param_values = list(param_grid.values())
            param_combinations = list(product(*param_values))
            
            logger.info(f"총 {len(param_combinations)}개의 파라미터 조합으로 최적화 진행")
            
            # 병렬 처리로 백테스트 실행
            results = []
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                future_to_params = {
                    executor.submit(self._run_grid_backtest, params, param_names): params 
                    for params in param_combinations
                }
                
                for future in as_completed(future_to_params):
                    params = future_to_params[future]
                    try:
                        result = future.result()
                        if result:
                            results.append(result)
                            logger.info(f"완료: {dict(zip(param_names, params))} -> {metric}: {result[metric]:.2f}")
                    except Exception as e:
                        logger.error(f"파라미터 {params} 백테스트 실패: {e}")
            
            results_df = pd.DataFrame(results)
            
            if not results_df.empty:
                results_df = results_df.sort_values(metric, ascending=False)
                best_params = results_df.iloc[0]
                logger.info(f"그리드 서치 완료: 최고 {metric} {best_params[metric]:.2f}")
                logger.info(f"최적 파라미터: {best_params.to_dict()}")
            
            return results_df
            
        except Exception as e:
            logger.error(f"그리드 서치 중 오류: {e}")
            return pd.DataFrame()
    
    def _run_grid_backtest(self, params: Tuple, param_names: List[str]) -> Dict[str, Any]:
        """
        그리드 서치용 백테스트 실행
        """
        try:
            # 파라미터 매핑
            param_dict = dict(zip(param_names, params))
            
            # 백테스트 엔진 생성
            engine = BacktestEngine(self.initial_capital)
            
            # 설정 적용
            from src.core.config import Config
            original_settings = {}
            
            for name, value in param_dict.items():
                if hasattr(Config, name.upper()):
                    original_settings[name] = getattr(Config, name.upper())
                    setattr(Config, name.upper(), value)
            
            # 백테스트 실행
            result = engine.run_backtest(self.data, self.symbol)
            
            # 설정 복원
            for name, value in original_settings.items():
                setattr(Config, name.upper(), value)
            
            # 결과 반환
            result_dict = param_dict.copy()
            result_dict.update({
                'total_return': result.total_return,
                'annualized_return': result.annualized_return,
                'sharpe_ratio': result.sharpe_ratio,
                'max_drawdown': result.max_drawdown,
                'total_trades': result.total_trades,
                'win_rate': result.win_rate,
                'profit_factor': result.profit_factor
            })
            
            return result_dict
            
        except Exception as e:
            logger.error(f"그리드 백테스트 실행 중 오류: {e}")
            return None
    
    def plot_optimization_results(self, results_df: pd.DataFrame, metric: str = 'total_return'):
        """
        최적화 결과 시각화
        """
        try:
            if results_df.empty:
                logger.warning("최적화 결과가 없습니다.")
                return
            
            # 상위 10개 결과만 선택
            top_results = results_df.head(10)
            
            plt.figure(figsize=(12, 8))
            
            # 메트릭별 막대 그래프
            plt.subplot(2, 2, 1)
            plt.bar(range(len(top_results)), top_results[metric])
            plt.title(f'Top 10 {metric}')
            plt.ylabel(metric)
            plt.xticks(range(len(top_results)), [f'#{i+1}' for i in range(len(top_results))])
            
            # 샤프 비율 vs 수익률
            plt.subplot(2, 2, 2)
            plt.scatter(top_results['sharpe_ratio'], top_results['total_return'])
            plt.xlabel('Sharpe Ratio')
            plt.ylabel('Total Return (%)')
            plt.title('Sharpe Ratio vs Total Return')
            
            # 최대 낙폭 vs 수익률
            plt.subplot(2, 2, 3)
            plt.scatter(top_results['max_drawdown'], top_results['total_return'])
            plt.xlabel('Max Drawdown (%)')
            plt.ylabel('Total Return (%)')
            plt.title('Max Drawdown vs Total Return')
            
            # 승률 vs 수익률
            plt.subplot(2, 2, 4)
            plt.scatter(top_results['win_rate'], top_results['total_return'])
            plt.xlabel('Win Rate (%)')
            plt.ylabel('Total Return (%)')
            plt.title('Win Rate vs Total Return')
            
            plt.tight_layout()
            plt.show()
            
        except Exception as e:
            logger.error(f"최적화 결과 시각화 중 오류: {e}")
    
    def export_optimization_results(self, results_df: pd.DataFrame, file_path: str):
        """
        최적화 결과를 CSV 파일로 내보내기
        """
        try:
            results_df.to_csv(file_path, index=False)
            logger.info(f"최적화 결과 내보내기 완료: {file_path}")
        except Exception as e:
            logger.error(f"최적화 결과 내보내기 중 오류: {e}") 