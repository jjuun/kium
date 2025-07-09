"""
백테스트 실행기
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import argparse
import json
from pathlib import Path

from src.core.logger import logger
from src.core.data_collector import DataCollector
from src.backtesting.backtest_engine import BacktestEngine, BacktestResult
from src.backtesting.backtest_analyzer import BacktestAnalyzer
from src.backtesting.strategy_optimizer import StrategyOptimizer

class BacktestRunner:
    def __init__(self):
        """
        백테스트 실행기 초기화
        """
        self.data_collector = DataCollector()
        
    def run_single_backtest(self, 
                           symbol: str,
                           start_date: str,
                           end_date: str,
                           initial_capital: float = 10000000,
                           strategy_params: Dict[str, Any] = None) -> BacktestResult:
        """
        단일 백테스트 실행
        
        Args:
            symbol: 종목 코드
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)
            initial_capital: 초기 자본금
            strategy_params: 전략 파라미터
            
        Returns:
            BacktestResult: 백테스트 결과
        """
        try:
            logger.info(f"백테스트 시작: {symbol}")
            logger.info(f"기간: {start_date} ~ {end_date}")
            logger.info(f"초기 자본: {initial_capital:,}원")
            
            # 데이터 수집
            data = self._collect_historical_data(symbol, start_date, end_date)
            if data is None or data.empty:
                raise ValueError(f"데이터 수집 실패: {symbol}")
            
            # 전략 파라미터 적용
            if strategy_params:
                self._apply_strategy_params(strategy_params)
            
            # 백테스트 엔진 생성 및 실행
            engine = BacktestEngine(initial_capital)
            result = engine.run_backtest(data, symbol, start_date, end_date)
            
            logger.info(f"백테스트 완료: {symbol}")
            logger.info(f"총 수익률: {result.total_return:.2f}%")
            logger.info(f"총 거래 횟수: {result.total_trades}")
            
            return result
            
        except Exception as e:
            logger.error(f"백테스트 실행 중 오류: {e}")
            raise
    
    def run_comparison_backtest(self, 
                               symbols: List[str],
                               start_date: str,
                               end_date: str,
                               initial_capital: float = 10000000) -> Dict[str, BacktestResult]:
        """
        다중 종목 비교 백테스트 실행
        
        Args:
            symbols: 종목 코드 리스트
            start_date: 시작 날짜
            end_date: 종료 날짜
            initial_capital: 초기 자본금
            
        Returns:
            Dict[str, BacktestResult]: 종목별 백테스트 결과
        """
        try:
            logger.info(f"비교 백테스트 시작: {len(symbols)}개 종목")
            
            results = {}
            for symbol in symbols:
                try:
                    result = self.run_single_backtest(
                        symbol, start_date, end_date, initial_capital
                    )
                    results[symbol] = result
                except Exception as e:
                    logger.error(f"{symbol} 백테스트 실패: {e}")
                    continue
            
            # 결과 비교 분석
            self._analyze_comparison_results(results)
            
            return results
            
        except Exception as e:
            logger.error(f"비교 백테스트 실행 중 오류: {e}")
            raise
    
    def run_optimization(self, 
                        symbol: str,
                        start_date: str,
                        end_date: str,
                        optimization_type: str = 'sma_crossover',
                        param_ranges: Dict[str, List[Any]] = None) -> pd.DataFrame:
        """
        전략 최적화 실행
        
        Args:
            symbol: 종목 코드
            start_date: 시작 날짜
            end_date: 종료 날짜
            optimization_type: 최적화 타입
            param_ranges: 파라미터 범위
            
        Returns:
            pd.DataFrame: 최적화 결과
        """
        try:
            logger.info(f"전략 최적화 시작: {symbol} - {optimization_type}")
            
            # 데이터 수집
            data = self._collect_historical_data(symbol, start_date, end_date)
            if data is None or data.empty:
                raise ValueError(f"데이터 수집 실패: {symbol}")
            
            # 최적화기 생성
            optimizer = StrategyOptimizer(data, symbol)
            
            # 최적화 타입별 실행
            if optimization_type == 'sma_crossover':
                results = optimizer.optimize_sma_crossover()
            elif optimization_type == 'risk_parameters':
                results = optimizer.optimize_risk_parameters()
            elif optimization_type == 'grid_search':
                if param_ranges is None:
                    param_ranges = {
                        'short_period': [3, 5, 8, 10],
                        'long_period': [15, 20, 25, 30],
                        'stop_loss': [2.0, 3.0, 5.0],
                        'take_profit': [5.0, 7.0, 10.0]
                    }
                results = optimizer.grid_search(param_ranges)
            else:
                raise ValueError(f"지원하지 않는 최적화 타입: {optimization_type}")
            
            # 최적화 결과 시각화
            if not results.empty:
                optimizer.plot_optimization_results(results)
                
                # 최적 파라미터로 백테스트 실행
                best_params = results.iloc[0].to_dict()
                logger.info(f"최적 파라미터: {best_params}")
                
                # 최적화 결과 저장
                self._save_optimization_results(results, symbol, optimization_type)
            
            return results
            
        except Exception as e:
            logger.error(f"전략 최적화 실행 중 오류: {e}")
            raise
    
    def _collect_historical_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        과거 데이터 수집
        """
        try:
            # 데이터 수집기에서 과거 데이터 가져오기
            data = self.data_collector.get_historical_data(symbol, start_date, end_date)
            
            if data is not None and not data.empty:
                logger.info(f"데이터 수집 완료: {symbol} - {len(data)}개 데이터")
                return data
            else:
                logger.error(f"데이터 수집 실패: {symbol}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"데이터 수집 중 오류: {e}")
            return pd.DataFrame()
    
    def _apply_strategy_params(self, params: Dict[str, Any]):
        """
        전략 파라미터 적용
        """
        try:
            from src.core.config import Config
            
            for key, value in params.items():
                if hasattr(Config, key.upper()):
                    setattr(Config, key.upper(), value)
                    logger.info(f"파라미터 설정: {key} = {value}")
                    
        except Exception as e:
            logger.error(f"전략 파라미터 적용 중 오류: {e}")
    
    def _analyze_comparison_results(self, results: Dict[str, BacktestResult]):
        """
        비교 결과 분석
        """
        try:
            logger.info("=== 비교 백테스트 결과 ===")
            
            # 결과 요약 테이블 생성
            summary_data = []
            for symbol, result in results.items():
                summary_data.append({
                    '종목': symbol,
                    '총 수익률 (%)': f"{result.total_return:.2f}",
                    '연간 수익률 (%)': f"{result.annualized_return:.2f}",
                    '샤프 비율': f"{result.sharpe_ratio:.3f}",
                    '최대 낙폭 (%)': f"{result.max_drawdown:.2f}",
                    '총 거래 횟수': result.total_trades,
                    '승률 (%)': f"{result.win_rate:.1f}",
                    '수익 팩터': f"{result.profit_factor:.3f}"
                })
            
            summary_df = pd.DataFrame(summary_data)
            print("\n" + summary_df.to_string(index=False))
            
            # 최고 성과 종목 찾기
            best_symbol = max(results.keys(), key=lambda x: results[x].total_return)
            best_result = results[best_symbol]
            
            logger.info(f"최고 성과 종목: {best_symbol}")
            logger.info(f"총 수익률: {best_result.total_return:.2f}%")
            logger.info(f"샤프 비율: {best_result.sharpe_ratio:.3f}")
            
        except Exception as e:
            logger.error(f"비교 결과 분석 중 오류: {e}")
    
    def _save_optimization_results(self, results: pd.DataFrame, symbol: str, optimization_type: str):
        """
        최적화 결과 저장
        """
        try:
            # 결과 디렉토리 생성
            results_dir = Path("backtest_results")
            results_dir.mkdir(exist_ok=True)
            
            # 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{symbol}_{optimization_type}_{timestamp}.csv"
            filepath = results_dir / filename
            
            # 결과 저장
            results.to_csv(filepath, index=False)
            logger.info(f"최적화 결과 저장: {filepath}")
            
        except Exception as e:
            logger.error(f"최적화 결과 저장 중 오류: {e}")
    
    def generate_report(self, result: BacktestResult, symbol: str, output_dir: str = "reports"):
        """
        백테스트 보고서 생성
        """
        try:
            # 출력 디렉토리 생성
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            
            # 분석기 생성
            analyzer = BacktestAnalyzer(result)
            
            # 요약 보고서 생성
            summary = analyzer.generate_summary_report()
            
            # 보고서 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = f"{symbol}_backtest_report_{timestamp}.json"
            report_path = output_path / report_filename
            
            # JSON 보고서 저장
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
            
            # 차트 생성
            charts_dir = output_path / "charts"
            charts_dir.mkdir(exist_ok=True)
            
            analyzer.plot_equity_curve(str(charts_dir / f"{symbol}_equity_curve.png"))
            analyzer.plot_drawdown(str(charts_dir / f"{symbol}_drawdown.png"))
            analyzer.plot_monthly_returns(str(charts_dir / f"{symbol}_monthly_returns.png"))
            analyzer.plot_trade_analysis(str(charts_dir / f"{symbol}_trade_analysis.png"))
            
            # 결과 데이터 내보내기
            data_filename = f"{symbol}_backtest_data_{timestamp}.csv"
            analyzer.export_results(str(output_path / data_filename))
            
            logger.info(f"백테스트 보고서 생성 완료: {report_path}")
            
        except Exception as e:
            logger.error(f"보고서 생성 중 오류: {e}")

def main():
    """
    메인 실행 함수
    """
    parser = argparse.ArgumentParser(description='백테스트 실행기')
    parser.add_argument('--symbol', type=str, required=True, help='종목 코드')
    parser.add_argument('--start_date', type=str, required=True, help='시작 날짜 (YYYY-MM-DD)')
    parser.add_argument('--end_date', type=str, required=True, help='종료 날짜 (YYYY-MM-DD)')
    parser.add_argument('--initial_capital', type=float, default=10000000, help='초기 자본금')
    parser.add_argument('--mode', type=str, choices=['single', 'optimization'], default='single', help='실행 모드')
    parser.add_argument('--optimization_type', type=str, choices=['sma_crossover', 'risk_parameters', 'grid_search'], help='최적화 타입')
    parser.add_argument('--generate_report', action='store_true', help='보고서 생성')
    
    args = parser.parse_args()
    
    try:
        runner = BacktestRunner()
        
        if args.mode == 'single':
            # 단일 백테스트 실행
            result = runner.run_single_backtest(
                args.symbol, args.start_date, args.end_date, args.initial_capital
            )
            
            if args.generate_report:
                runner.generate_report(result, args.symbol)
                
        elif args.mode == 'optimization':
            # 최적화 실행
            if not args.optimization_type:
                raise ValueError("최적화 모드에서는 optimization_type이 필요합니다.")
            
            results = runner.run_optimization(
                args.symbol, args.start_date, args.end_date, args.optimization_type
            )
            
            print(f"\n최적화 결과 (상위 5개):")
            print(results.head().to_string(index=False))
    
    except Exception as e:
        logger.error(f"백테스트 실행 중 오류: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 