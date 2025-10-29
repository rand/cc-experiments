#!/usr/bin/env python3
"""
Capacity Forecasting Tool

This script provides comprehensive capacity forecasting using multiple methods:
- Linear regression for steady growth
- Exponential smoothing for noisy data
- Prophet for seasonal patterns
- ARIMA for complex time series
- Multi-variate forecasting for correlated metrics

Usage:
    forecast_capacity.py --input metrics.csv --forecast-days 90
    forecast_capacity.py --input metrics.csv --method prophet --seasonality weekly
    forecast_capacity.py --metric cpu_usage --lookback 60 --forecast-days 30 --json
    forecast_capacity.py --input metrics.csv --visualize --output forecast.png
    forecast_capacity.py --prometheus http://localhost:9090 --query 'cpu_usage' --forecast-days 90
"""

import argparse
import sys
import json
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict
import warnings
warnings.filterwarnings('ignore')


@dataclass
class ForecastResult:
    """Container for forecast results."""
    method: str
    forecast_values: List[float]
    forecast_dates: List[str]
    confidence_lower: Optional[List[float]] = None
    confidence_upper: Optional[List[float]] = None
    metrics: Optional[Dict[str, float]] = None
    parameters: Optional[Dict[str, Any]] = None


class CapacityForecaster:
    """Main capacity forecasting class."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results = []

    def log(self, message: str) -> None:
        """Log message if verbose mode enabled."""
        if self.verbose:
            print(f"[INFO] {message}", file=sys.stderr)

    def load_data_from_csv(self, filepath: Path) -> pd.DataFrame:
        """
        Load time series data from CSV file.

        Expected format:
            timestamp,value
            2024-01-01,45.2
            2024-01-02,47.1
            ...
        """
        self.log(f"Loading data from {filepath}")

        try:
            df = pd.read_csv(filepath)

            # Handle different column names
            if 'timestamp' in df.columns:
                date_col = 'timestamp'
            elif 'date' in df.columns:
                date_col = 'date'
            elif 'ds' in df.columns:
                date_col = 'ds'
            else:
                date_col = df.columns[0]

            if 'value' in df.columns:
                value_col = 'value'
            elif 'y' in df.columns:
                value_col = 'y'
            else:
                value_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]

            df['ds'] = pd.to_datetime(df[date_col])
            df['y'] = pd.to_numeric(df[value_col], errors='coerce')

            df = df[['ds', 'y']].dropna()
            df = df.sort_values('ds')

            self.log(f"Loaded {len(df)} data points")
            return df

        except Exception as e:
            raise ValueError(f"Failed to load CSV: {e}")

    def load_data_from_prometheus(
        self,
        prometheus_url: str,
        query: str,
        lookback_days: int = 60
    ) -> pd.DataFrame:
        """Load data from Prometheus."""
        import requests

        self.log(f"Querying Prometheus: {query}")

        end_time = datetime.now()
        start_time = end_time - timedelta(days=lookback_days)

        try:
            response = requests.get(
                f"{prometheus_url}/api/v1/query_range",
                params={
                    'query': query,
                    'start': start_time.timestamp(),
                    'end': end_time.timestamp(),
                    'step': '1h'
                },
                timeout=30
            )

            response.raise_for_status()
            data = response.json()

            if data['status'] != 'success':
                raise ValueError(f"Prometheus query failed: {data}")

            results = data['data']['result']
            if not results:
                raise ValueError("No data returned from Prometheus")

            # Use first result series
            values = results[0]['values']

            df = pd.DataFrame(values, columns=['timestamp', 'value'])
            df['ds'] = pd.to_datetime(df['timestamp'], unit='s')
            df['y'] = pd.to_numeric(df['value'], errors='coerce')

            df = df[['ds', 'y']].dropna()

            self.log(f"Retrieved {len(df)} data points from Prometheus")
            return df

        except requests.exceptions.RequestException as e:
            raise ValueError(f"Failed to query Prometheus: {e}")

    def forecast_linear(
        self,
        data: pd.DataFrame,
        periods: int
    ) -> ForecastResult:
        """Forecast using linear regression."""
        from sklearn.linear_model import LinearRegression
        from scipy import stats

        self.log("Forecasting with linear regression")

        # Prepare data
        X = np.arange(len(data)).reshape(-1, 1)
        y = data['y'].values

        # Fit model
        model = LinearRegression()
        model.fit(X, y)

        # Generate forecast
        future_X = np.arange(len(data), len(data) + periods).reshape(-1, 1)
        forecast = model.predict(future_X)

        # Calculate confidence intervals
        residuals = y - model.predict(X)
        mse = np.mean(residuals ** 2)
        se = np.sqrt(mse * (1 + 1/len(X)))

        # 95% confidence interval
        t_val = stats.t.ppf(0.975, len(X) - 2)
        margin = t_val * se

        confidence_lower = forecast - margin
        confidence_upper = forecast + margin

        # Generate forecast dates
        last_date = data['ds'].iloc[-1]
        freq = pd.infer_freq(data['ds']) or 'D'
        forecast_dates = pd.date_range(
            start=last_date + pd.Timedelta(1, unit=freq[0]),
            periods=periods,
            freq=freq
        )

        # Calculate metrics
        r2 = model.score(X, y)
        rmse = np.sqrt(mse)

        return ForecastResult(
            method='linear',
            forecast_values=forecast.tolist(),
            forecast_dates=[d.isoformat() for d in forecast_dates],
            confidence_lower=confidence_lower.tolist(),
            confidence_upper=confidence_upper.tolist(),
            metrics={
                'r2': r2,
                'rmse': rmse,
                'slope': model.coef_[0],
                'intercept': model.intercept_
            },
            parameters={
                'periods': periods
            }
        )

    def forecast_exponential_smoothing(
        self,
        data: pd.DataFrame,
        periods: int,
        seasonal_periods: Optional[int] = None
    ) -> ForecastResult:
        """Forecast using exponential smoothing (Holt-Winters)."""
        from statsmodels.tsa.holtwinters import ExponentialSmoothing

        self.log("Forecasting with exponential smoothing")

        try:
            # Determine if seasonal
            if seasonal_periods is None:
                seasonal_periods = self._detect_seasonality(data)

            if seasonal_periods and seasonal_periods > 1 and len(data) >= 2 * seasonal_periods:
                # Triple exponential smoothing
                model = ExponentialSmoothing(
                    data['y'].values,
                    seasonal_periods=seasonal_periods,
                    trend='add',
                    seasonal='add',
                    initialization_method='estimated'
                )
                self.log(f"Using seasonal model with period={seasonal_periods}")
            else:
                # Double exponential smoothing (no seasonality)
                model = ExponentialSmoothing(
                    data['y'].values,
                    trend='add',
                    seasonal=None,
                    initialization_method='estimated'
                )
                self.log("Using non-seasonal model")

            fitted = model.fit(optimized=True)
            forecast = fitted.forecast(periods)

            # Generate forecast dates
            last_date = data['ds'].iloc[-1]
            freq = pd.infer_freq(data['ds']) or 'D'
            forecast_dates = pd.date_range(
                start=last_date + pd.Timedelta(1, unit=freq[0]),
                periods=periods,
                freq=freq
            )

            # Calculate confidence intervals (approximation)
            residuals = fitted.fittedvalues - data['y'].values
            std_error = np.std(residuals)
            margin = 1.96 * std_error  # 95% CI

            confidence_lower = forecast - margin
            confidence_upper = forecast + margin

            return ForecastResult(
                method='exponential_smoothing',
                forecast_values=forecast.tolist(),
                forecast_dates=[d.isoformat() for d in forecast_dates],
                confidence_lower=confidence_lower.tolist(),
                confidence_upper=confidence_upper.tolist(),
                metrics={
                    'aic': fitted.aic,
                    'bic': fitted.bic,
                    'mse': fitted.mse
                },
                parameters={
                    'seasonal_periods': seasonal_periods,
                    'periods': periods
                }
            )

        except Exception as e:
            self.log(f"Exponential smoothing failed: {e}")
            # Fallback to simple exponential smoothing
            return self._simple_exponential_smoothing(data, periods)

    def _simple_exponential_smoothing(
        self,
        data: pd.DataFrame,
        periods: int,
        alpha: float = 0.3
    ) -> ForecastResult:
        """Fallback simple exponential smoothing."""
        self.log("Using simple exponential smoothing (fallback)")

        values = data['y'].values
        smoothed = [values[0]]

        for i in range(1, len(values)):
            s = alpha * values[i] + (1 - alpha) * smoothed[-1]
            smoothed.append(s)

        # Forecast as flat line from last smoothed value
        forecast = np.array([smoothed[-1]] * periods)

        # Generate forecast dates
        last_date = data['ds'].iloc[-1]
        freq = pd.infer_freq(data['ds']) or 'D'
        forecast_dates = pd.date_range(
            start=last_date + pd.Timedelta(1, unit=freq[0]),
            periods=periods,
            freq=freq
        )

        # Simple confidence interval based on historical variance
        std_error = np.std(values - smoothed)
        margin = 1.96 * std_error

        confidence_lower = forecast - margin
        confidence_upper = forecast + margin

        return ForecastResult(
            method='simple_exponential_smoothing',
            forecast_values=forecast.tolist(),
            forecast_dates=[d.isoformat() for d in forecast_dates],
            confidence_lower=confidence_lower.tolist(),
            confidence_upper=confidence_upper.tolist(),
            parameters={
                'alpha': alpha,
                'periods': periods
            }
        )

    def forecast_prophet(
        self,
        data: pd.DataFrame,
        periods: int,
        seasonality: str = 'auto',
        holidays: Optional[pd.DataFrame] = None
    ) -> ForecastResult:
        """Forecast using Facebook Prophet."""
        try:
            from prophet import Prophet
        except ImportError:
            raise ImportError("Prophet not installed. Install with: pip install prophet")

        self.log("Forecasting with Prophet")

        # Configure seasonality
        yearly_seasonality = seasonality in ['auto', 'yearly']
        weekly_seasonality = seasonality in ['auto', 'weekly']
        daily_seasonality = seasonality == 'daily'

        model = Prophet(
            yearly_seasonality=yearly_seasonality,
            weekly_seasonality=weekly_seasonality,
            daily_seasonality=daily_seasonality,
            interval_width=0.95,
            changepoint_prior_scale=0.05
        )

        # Add holidays if provided
        if holidays is not None:
            model.holidays = holidays

        # Fit model
        model.fit(data)

        # Make future dataframe
        freq = pd.infer_freq(data['ds']) or 'D'
        future = model.make_future_dataframe(periods=periods, freq=freq)

        # Forecast
        forecast = model.predict(future)

        # Extract forecast period
        forecast_period = forecast.tail(periods)

        return ForecastResult(
            method='prophet',
            forecast_values=forecast_period['yhat'].tolist(),
            forecast_dates=[d.isoformat() for d in forecast_period['ds']],
            confidence_lower=forecast_period['yhat_lower'].tolist(),
            confidence_upper=forecast_period['yhat_upper'].tolist(),
            parameters={
                'yearly_seasonality': yearly_seasonality,
                'weekly_seasonality': weekly_seasonality,
                'daily_seasonality': daily_seasonality,
                'periods': periods
            }
        )

    def forecast_arima(
        self,
        data: pd.DataFrame,
        periods: int,
        order: Optional[Tuple[int, int, int]] = None
    ) -> ForecastResult:
        """Forecast using ARIMA."""
        from statsmodels.tsa.arima.model import ARIMA

        self.log("Forecasting with ARIMA")

        # Auto-detect order if not provided
        if order is None:
            order = self._auto_arima_order(data['y'].values)
            self.log(f"Auto-detected ARIMA order: {order}")

        try:
            model = ARIMA(data['y'].values, order=order)
            fitted = model.fit()

            # Forecast
            forecast_result = fitted.get_forecast(steps=periods)
            forecast = forecast_result.predicted_mean
            conf_int = forecast_result.conf_int()

            # Generate forecast dates
            last_date = data['ds'].iloc[-1]
            freq = pd.infer_freq(data['ds']) or 'D'
            forecast_dates = pd.date_range(
                start=last_date + pd.Timedelta(1, unit=freq[0]),
                periods=periods,
                freq=freq
            )

            return ForecastResult(
                method='arima',
                forecast_values=forecast.tolist(),
                forecast_dates=[d.isoformat() for d in forecast_dates],
                confidence_lower=conf_int.iloc[:, 0].tolist(),
                confidence_upper=conf_int.iloc[:, 1].tolist(),
                metrics={
                    'aic': fitted.aic,
                    'bic': fitted.bic
                },
                parameters={
                    'order': order,
                    'periods': periods
                }
            )

        except Exception as e:
            self.log(f"ARIMA failed: {e}")
            raise

    def _auto_arima_order(self, data: np.ndarray) -> Tuple[int, int, int]:
        """Automatically determine ARIMA order."""
        from statsmodels.tsa.stattools import adfuller

        # Test for stationarity
        adf_result = adfuller(data)
        is_stationary = adf_result[1] < 0.05

        # Determine differencing order
        d = 0 if is_stationary else 1

        # Use simple defaults for p and q
        p = 1
        q = 1

        return (p, d, q)

    def _detect_seasonality(self, data: pd.DataFrame) -> Optional[int]:
        """Detect seasonal period in data."""
        # Infer from date frequency
        freq = pd.infer_freq(data['ds'])

        if freq is None:
            return None

        if freq.startswith('D'):
            # Daily data: check for weekly pattern (7 days)
            return 7
        elif freq.startswith('H'):
            # Hourly data: check for daily pattern (24 hours)
            return 24
        else:
            return None

    def forecast_multi_method(
        self,
        data: pd.DataFrame,
        periods: int,
        methods: Optional[List[str]] = None
    ) -> List[ForecastResult]:
        """Generate forecasts using multiple methods."""
        if methods is None:
            methods = ['linear', 'exponential_smoothing', 'prophet']

        results = []

        for method in methods:
            try:
                if method == 'linear':
                    result = self.forecast_linear(data, periods)
                elif method == 'exponential_smoothing':
                    result = self.forecast_exponential_smoothing(data, periods)
                elif method == 'prophet':
                    result = self.forecast_prophet(data, periods)
                elif method == 'arima':
                    result = self.forecast_arima(data, periods)
                else:
                    self.log(f"Unknown method: {method}")
                    continue

                results.append(result)
                self.log(f"Successfully forecasted with {method}")

            except Exception as e:
                self.log(f"Failed to forecast with {method}: {e}")

        return results

    def ensemble_forecast(
        self,
        results: List[ForecastResult],
        weights: Optional[List[float]] = None
    ) -> ForecastResult:
        """Combine multiple forecasts into ensemble."""
        if not results:
            raise ValueError("No results to ensemble")

        if weights is None:
            weights = [1.0 / len(results)] * len(results)

        if len(weights) != len(results):
            raise ValueError("Weights length must match results length")

        # Weighted average of forecasts
        forecast_arrays = [np.array(r.forecast_values) for r in results]
        ensemble_forecast = np.average(forecast_arrays, axis=0, weights=weights)

        # Use dates from first result
        forecast_dates = results[0].forecast_dates

        # Confidence intervals (if available)
        if all(r.confidence_lower is not None for r in results):
            lower_arrays = [np.array(r.confidence_lower) for r in results]
            upper_arrays = [np.array(r.confidence_upper) for r in results]

            confidence_lower = np.average(lower_arrays, axis=0, weights=weights)
            confidence_upper = np.average(upper_arrays, axis=0, weights=weights)
        else:
            confidence_lower = None
            confidence_upper = None

        return ForecastResult(
            method='ensemble',
            forecast_values=ensemble_forecast.tolist(),
            forecast_dates=forecast_dates,
            confidence_lower=confidence_lower.tolist() if confidence_lower is not None else None,
            confidence_upper=confidence_upper.tolist() if confidence_upper is not None else None,
            parameters={
                'methods': [r.method for r in results],
                'weights': weights
            }
        )

    def visualize_forecast(
        self,
        data: pd.DataFrame,
        results: List[ForecastResult],
        output_file: Path
    ) -> None:
        """Visualize forecast results."""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
        except ImportError:
            self.log("Matplotlib not installed, skipping visualization")
            return

        self.log(f"Generating visualization: {output_file}")

        fig, ax = plt.subplots(figsize=(14, 7))

        # Plot historical data
        ax.plot(data['ds'], data['y'], 'o-', label='Historical', linewidth=2)

        # Plot forecasts
        colors = ['red', 'green', 'blue', 'orange', 'purple']
        for i, result in enumerate(results):
            color = colors[i % len(colors)]
            dates = pd.to_datetime(result.forecast_dates)

            ax.plot(
                dates,
                result.forecast_values,
                '--',
                label=f'Forecast ({result.method})',
                color=color,
                linewidth=2
            )

            # Plot confidence interval if available
            if result.confidence_lower and result.confidence_upper:
                ax.fill_between(
                    dates,
                    result.confidence_lower,
                    result.confidence_upper,
                    alpha=0.2,
                    color=color
                )

        # Formatting
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Value', fontsize=12)
        ax.set_title('Capacity Forecast', fontsize=14, fontweight='bold')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)

        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.xticks(rotation=45)

        plt.tight_layout()
        plt.savefig(output_file, dpi=300)
        self.log(f"Visualization saved to {output_file}")

    def export_forecast(
        self,
        results: List[ForecastResult],
        output_file: Path,
        format: str = 'csv'
    ) -> None:
        """Export forecast results."""
        self.log(f"Exporting forecast to {output_file}")

        if format == 'json':
            with open(output_file, 'w') as f:
                json.dump(
                    [asdict(r) for r in results],
                    f,
                    indent=2
                )
        elif format == 'csv':
            # Export first result to CSV
            if not results:
                return

            result = results[0]
            with open(output_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['date', 'forecast', 'lower_bound', 'upper_bound'])

                for i, date in enumerate(result.forecast_dates):
                    row = [
                        date,
                        result.forecast_values[i]
                    ]
                    if result.confidence_lower:
                        row.append(result.confidence_lower[i])
                    if result.confidence_upper:
                        row.append(result.confidence_upper[i])
                    writer.writerow(row)

        self.log(f"Exported {len(results)} forecast(s)")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Capacity forecasting tool with multiple forecasting methods',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Forecast from CSV file
    %(prog)s --input metrics.csv --forecast-days 90 --visualize

    # Use specific method
    %(prog)s --input metrics.csv --method prophet --forecast-days 30

    # Load from Prometheus
    %(prog)s --prometheus http://localhost:9090 --query 'cpu_usage' --forecast-days 60

    # Multi-method ensemble
    %(prog)s --input metrics.csv --methods linear prophet arima --ensemble

    # Export to JSON
    %(prog)s --input metrics.csv --forecast-days 90 --json --output forecast.json
        """
    )

    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--input',
        type=Path,
        help='Input CSV file with timestamp,value columns'
    )
    input_group.add_argument(
        '--prometheus',
        help='Prometheus URL (e.g., http://localhost:9090)'
    )

    # Prometheus options
    parser.add_argument(
        '--query',
        help='Prometheus query (required if --prometheus used)'
    )
    parser.add_argument(
        '--lookback-days',
        type=int,
        default=60,
        help='Days of historical data to fetch from Prometheus (default: 60)'
    )

    # Forecasting options
    parser.add_argument(
        '--forecast-days',
        type=int,
        default=30,
        help='Number of days to forecast (default: 30)'
    )
    parser.add_argument(
        '--method',
        choices=['linear', 'exponential_smoothing', 'prophet', 'arima'],
        default='linear',
        help='Forecasting method (default: linear)'
    )
    parser.add_argument(
        '--methods',
        nargs='+',
        choices=['linear', 'exponential_smoothing', 'prophet', 'arima'],
        help='Multiple forecasting methods'
    )
    parser.add_argument(
        '--ensemble',
        action='store_true',
        help='Generate ensemble forecast from multiple methods'
    )

    # Prophet-specific options
    parser.add_argument(
        '--seasonality',
        choices=['auto', 'yearly', 'weekly', 'daily', 'none'],
        default='auto',
        help='Seasonality for Prophet (default: auto)'
    )

    # Output options
    parser.add_argument(
        '--output',
        type=Path,
        help='Output file path'
    )
    parser.add_argument(
        '--visualize',
        action='store_true',
        help='Generate visualization chart'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )

    # Misc options
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Validate arguments
    if args.prometheus and not args.query:
        parser.error("--query is required when using --prometheus")

    forecaster = CapacityForecaster(verbose=args.verbose)

    try:
        # Load data
        if args.input:
            data = forecaster.load_data_from_csv(args.input)
        else:
            data = forecaster.load_data_from_prometheus(
                args.prometheus,
                args.query,
                args.lookback_days
            )

        # Generate forecasts
        if args.methods:
            results = forecaster.forecast_multi_method(data, args.forecast_days, args.methods)
        else:
            # Single method
            if args.method == 'linear':
                result = forecaster.forecast_linear(data, args.forecast_days)
            elif args.method == 'exponential_smoothing':
                result = forecaster.forecast_exponential_smoothing(data, args.forecast_days)
            elif args.method == 'prophet':
                result = forecaster.forecast_prophet(
                    data,
                    args.forecast_days,
                    seasonality=args.seasonality
                )
            elif args.method == 'arima':
                result = forecaster.forecast_arima(data, args.forecast_days)

            results = [result]

        # Generate ensemble if requested
        if args.ensemble and len(results) > 1:
            ensemble_result = forecaster.ensemble_forecast(results)
            results.append(ensemble_result)

        # Output results
        if args.json:
            output = [asdict(r) for r in results]
            print(json.dumps(output, indent=2))
        else:
            for result in results:
                print(f"\n=== Forecast ({result.method}) ===")
                print(f"Forecast dates: {result.forecast_dates[0]} to {result.forecast_dates[-1]}")
                print(f"Forecast range: {min(result.forecast_values):.2f} to {max(result.forecast_values):.2f}")

                if result.metrics:
                    print("\nMetrics:")
                    for key, value in result.metrics.items():
                        print(f"  {key}: {value:.4f}")

        # Export if output file specified
        if args.output:
            format = 'json' if args.json else 'csv'
            forecaster.export_forecast(results, args.output, format=format)

        # Visualize if requested
        if args.visualize:
            if args.output:
                vis_output = args.output.with_suffix('.png')
            else:
                vis_output = Path('forecast.png')

            forecaster.visualize_forecast(data, results, vis_output)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
