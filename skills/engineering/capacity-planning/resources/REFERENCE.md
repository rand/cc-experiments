# Capacity Planning - Comprehensive Reference

**Version**: 1.0
**Last Updated**: 2025-10-29
**Lines**: 3,200+

This document provides comprehensive technical reference material for capacity planning, covering forecasting methods, resource modeling, load testing, scaling strategies, cost optimization, and disaster recovery planning.

---

## Table of Contents

1. [Capacity Planning Fundamentals](#1-capacity-planning-fundamentals)
2. [Forecasting Methods](#2-forecasting-methods)
3. [Resource Modeling](#3-resource-modeling)
4. [Load Testing](#4-load-testing)
5. [Scaling Strategies](#5-scaling-strategies)
6. [Cost Optimization](#6-cost-optimization)
7. [Cloud Resource Planning](#7-cloud-resource-planning)
8. [Database Capacity Planning](#8-database-capacity-planning)
9. [Network Capacity Planning](#9-network-capacity-planning)
10. [Traffic Analysis and Prediction](#10-traffic-analysis-and-prediction)
11. [Disaster Recovery Capacity](#11-disaster-recovery-capacity)
12. [Compliance and Headroom](#12-compliance-and-headroom)
13. [Capacity Planning Tools](#13-capacity-planning-tools)
14. [Production Best Practices](#14-production-best-practices)

---

## 1. Capacity Planning Fundamentals

### 1.1 Overview

Capacity planning is the process of determining the infrastructure and resources needed to meet current and future demand while maintaining performance, reliability, and cost efficiency.

**Core Principles**:

```
Measure → Forecast → Plan → Provision → Monitor → Optimize
   ↓         ↓        ↓        ↓          ↓         ↓
Current   Future   Resource  Deploy    Validate  Improve
 State    Needs    Design    Changes   Results   Process
```

### 1.2 Planning Horizons

**Immediate (Days to Weeks)**:
- Emergency capacity additions
- Handling unexpected traffic spikes
- Addressing critical resource constraints
- Quick wins and optimizations

**Short-term (1-3 Months)**:
- Known product launches
- Marketing campaigns
- Seasonal traffic patterns
- Planned migrations and upgrades

**Medium-term (3-6 Months)**:
- Steady business growth
- Architecture improvements
- Cost optimization initiatives
- Technology refreshes

**Long-term (6-12+ Months)**:
- Strategic business objectives
- Major architecture changes
- Multi-year infrastructure planning
- Technology roadmap alignment

### 1.3 Resource Types

**Compute Resources**:
- CPU cores, vCPUs, processing capacity
- GPU resources for ML workloads
- Specialized processors (ARM, RISC-V)
- Container and serverless capacity

**Memory Resources**:
- RAM for application workloads
- Cache memory (L1, L2, L3)
- GPU memory
- Shared memory pools

**Storage Resources**:
- Disk space (HDD, SSD, NVMe)
- IOPS (Input/Output Operations Per Second)
- Throughput (MB/s, GB/s)
- Object storage capacity

**Network Resources**:
- Bandwidth (Mbps, Gbps)
- Packet processing capacity (pps)
- Connection limits
- Latency requirements

**Application Resources**:
- Database connections
- Worker threads/processes
- Queue capacity
- Session storage

### 1.4 Little's Law

**Formula**: `L = λ × W`

Where:
- `L` = Average number of items in system
- `λ` (lambda) = Average arrival rate
- `W` = Average time item spends in system

**Example**:
```
Web API handling 100 requests/second
Average response time: 200ms

L = 100 req/s × 0.2s = 20 concurrent requests

Need capacity for at least 20 concurrent connections
With 30% headroom: 26 concurrent connections
```

**Applications**:
- Sizing connection pools
- Determining queue depths
- Calculating concurrent user capacity
- Estimating worker thread requirements

### 1.5 Queueing Theory Basics

**M/M/1 Queue** (Markovian arrivals, Markovian service, 1 server):

```
Utilization: ρ = λ / μ

Where:
- λ = Arrival rate
- μ = Service rate
- ρ = Utilization (must be < 1 for stability)

Average queue length: Lq = ρ² / (1 - ρ)
Average wait time: Wq = Lq / λ
Average response time: W = Wq + (1/μ)
```

**Example**:
```
λ = 80 requests/second
μ = 100 requests/second (service rate)
ρ = 80/100 = 0.8 (80% utilization)

Lq = 0.8² / (1 - 0.8) = 0.64 / 0.2 = 3.2 requests in queue
Wq = 3.2 / 80 = 0.04 seconds = 40ms wait time
```

**Key Insight**: Queue length grows non-linearly as utilization approaches 100%. At 90% utilization, queues are 9x longer than at 50% utilization.

### 1.6 Capacity Planning Process

**Phase 1: Data Collection**
1. Gather historical metrics (CPU, memory, disk, network)
2. Document current architecture and capacity
3. Identify peak usage patterns
4. Collect business growth projections
5. Document upcoming launches/events
6. Identify constraints and dependencies

**Phase 2: Analysis**
1. Analyze trends and patterns
2. Identify bottlenecks and constraints
3. Calculate current utilization
4. Determine headroom remaining
5. Project time to capacity exhaustion

**Phase 3: Forecasting**
1. Choose appropriate forecasting method
2. Generate forecasts with confidence intervals
3. Account for known future events
4. Model multiple scenarios
5. Review with stakeholders

**Phase 4: Planning**
1. Calculate required resources
2. Design scaling approach
3. Estimate costs
4. Create implementation timeline
5. Identify risks and dependencies
6. Document decisions

**Phase 5: Implementation**
1. Provision resources
2. Configure auto-scaling
3. Update monitoring
4. Test capacity changes
5. Document changes

**Phase 6: Validation**
1. Monitor actual vs predicted capacity
2. Conduct load testing
3. Measure performance impact
4. Validate cost estimates
5. Update forecasts

---

## 2. Forecasting Methods

### 2.1 Linear Regression

**When to Use**:
- Steady, predictable growth
- No strong seasonal patterns
- Short to medium-term forecasts (3-6 months)

**Formula**: `y = mx + b`

Where:
- `y` = Predicted value
- `m` = Slope (growth rate)
- `x` = Time period
- `b` = Intercept (baseline)

**Python Implementation**:
```python
import numpy as np
from sklearn.linear_model import LinearRegression

def linear_forecast(historical_data: np.ndarray, periods_ahead: int):
    """
    Forecast using linear regression.

    Args:
        historical_data: Array of historical values
        periods_ahead: Number of periods to forecast

    Returns:
        Array of forecasted values
    """
    # Prepare training data
    X = np.arange(len(historical_data)).reshape(-1, 1)
    y = historical_data

    # Fit model
    model = LinearRegression()
    model.fit(X, y)

    # Generate forecast
    future_X = np.arange(len(historical_data),
                         len(historical_data) + periods_ahead).reshape(-1, 1)
    forecast = model.predict(future_X)

    return forecast, model.coef_[0], model.intercept_

# Example usage
historical_cpu = np.array([45, 48, 52, 55, 58, 61, 64, 67, 70, 73])
forecast, growth_rate, baseline = linear_forecast(historical_cpu, 12)

print(f"Growth rate: {growth_rate:.2f}% per period")
print(f"Baseline: {baseline:.2f}%")
print(f"12-period forecast: {forecast}")
```

**Confidence Intervals**:
```python
from scipy import stats

def linear_forecast_with_confidence(historical_data, periods_ahead, confidence=0.95):
    """Linear forecast with confidence intervals."""
    X = np.arange(len(historical_data)).reshape(-1, 1)
    y = historical_data

    model = LinearRegression()
    model.fit(X, y)

    # Predict
    future_X = np.arange(len(historical_data),
                         len(historical_data) + periods_ahead).reshape(-1, 1)
    forecast = model.predict(future_X)

    # Calculate standard error
    residuals = y - model.predict(X)
    mse = np.mean(residuals ** 2)
    se = np.sqrt(mse * (1 + 1/len(X)))

    # Confidence interval
    t_val = stats.t.ppf((1 + confidence) / 2, len(X) - 2)
    margin = t_val * se

    return {
        'forecast': forecast,
        'lower_bound': forecast - margin,
        'upper_bound': forecast + margin,
        'confidence': confidence
    }
```

### 2.2 Exponential Smoothing

**When to Use**:
- Recent data more important than old data
- Smooth out noise and fluctuations
- Short-term forecasts

**Simple Exponential Smoothing**:
```python
def simple_exponential_smoothing(data, alpha=0.3, periods_ahead=12):
    """
    Simple exponential smoothing.

    Args:
        data: Historical time series
        alpha: Smoothing parameter (0-1, higher = more weight on recent)
        periods_ahead: Forecast horizon

    Returns:
        Smoothed values and forecast
    """
    smoothed = [data[0]]

    for i in range(1, len(data)):
        s = alpha * data[i] + (1 - alpha) * smoothed[-1]
        smoothed.append(s)

    # Forecast (flat line from last smoothed value)
    forecast = [smoothed[-1]] * periods_ahead

    return np.array(smoothed), np.array(forecast)

# Example
data = np.array([100, 105, 103, 108, 110, 115, 112, 118, 120, 125])
smoothed, forecast = simple_exponential_smoothing(data, alpha=0.3, periods_ahead=6)
```

**Double Exponential Smoothing (Holt's Method)**:
```python
def double_exponential_smoothing(data, alpha=0.3, beta=0.1, periods_ahead=12):
    """
    Double exponential smoothing for data with trend.

    Args:
        data: Historical time series
        alpha: Level smoothing parameter
        beta: Trend smoothing parameter
        periods_ahead: Forecast horizon
    """
    # Initialize
    level = data[0]
    trend = data[1] - data[0]

    levels = [level]
    trends = [trend]

    # Smooth
    for i in range(1, len(data)):
        last_level = levels[-1]
        level = alpha * data[i] + (1 - alpha) * (last_level + trends[-1])
        trend = beta * (level - last_level) + (1 - beta) * trends[-1]

        levels.append(level)
        trends.append(trend)

    # Forecast
    forecast = []
    for i in range(1, periods_ahead + 1):
        forecast.append(levels[-1] + i * trends[-1])

    return np.array(levels), np.array(trends), np.array(forecast)
```

**Triple Exponential Smoothing (Holt-Winters)**:
```python
from statsmodels.tsa.holtwinters import ExponentialSmoothing

def holt_winters_forecast(data, seasonal_periods=7, periods_ahead=30):
    """
    Holt-Winters triple exponential smoothing with seasonality.

    Args:
        data: Historical time series
        seasonal_periods: Length of seasonal cycle (7 for weekly)
        periods_ahead: Forecast horizon
    """
    model = ExponentialSmoothing(
        data,
        seasonal_periods=seasonal_periods,
        trend='add',
        seasonal='add'
    )

    fitted = model.fit()
    forecast = fitted.forecast(periods_ahead)

    return {
        'fitted_values': fitted.fittedvalues,
        'forecast': forecast,
        'level': fitted.level,
        'trend': fitted.trend,
        'seasonal': fitted.season
    }

# Example with weekly seasonality
daily_requests = np.array([...])  # 90 days of data
result = holt_winters_forecast(daily_requests, seasonal_periods=7, periods_ahead=30)
```

### 2.3 ARIMA Models

**When to Use**:
- Complex patterns and autocorrelation
- Stationary or trend-stationary data
- Medium-term forecasts
- When you need statistical rigor

**ARIMA Parameters**:
- `p`: Order of autoregressive (AR) component
- `d`: Degree of differencing
- `q`: Order of moving average (MA) component

**Python Implementation**:
```python
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf

def find_arima_order(data):
    """Determine ARIMA order using statistical tests."""
    # Test for stationarity
    adf_result = adfuller(data)
    is_stationary = adf_result[1] < 0.05

    d = 0 if is_stationary else 1

    # If not stationary, difference the data
    if d > 0:
        differenced = np.diff(data)
    else:
        differenced = data

    # Use ACF/PACF to estimate p and q
    # (In practice, use grid search or auto_arima)

    return (1, d, 1)  # Simplified

def arima_forecast(data, order=None, periods_ahead=30):
    """
    ARIMA forecasting.

    Args:
        data: Historical time series
        order: (p, d, q) tuple, or None for auto-detection
        periods_ahead: Forecast horizon
    """
    if order is None:
        order = find_arima_order(data)

    model = ARIMA(data, order=order)
    fitted = model.fit()

    forecast = fitted.forecast(steps=periods_ahead)

    # Get confidence intervals
    forecast_result = fitted.get_forecast(steps=periods_ahead)
    conf_int = forecast_result.conf_int()

    return {
        'forecast': forecast,
        'lower_bound': conf_int.iloc[:, 0],
        'upper_bound': conf_int.iloc[:, 1],
        'aic': fitted.aic,
        'bic': fitted.bic,
        'order': order
    }

# Example
cpu_usage = np.array([...])  # Historical CPU usage
result = arima_forecast(cpu_usage, order=(1, 1, 1), periods_ahead=60)
```

**Auto ARIMA**:
```python
from pmdarima import auto_arima

def auto_arima_forecast(data, seasonal=True, m=7):
    """
    Automatic ARIMA model selection.

    Args:
        data: Historical time series
        seasonal: Whether to model seasonality
        m: Seasonal period
    """
    model = auto_arima(
        data,
        start_p=0, start_q=0,
        max_p=5, max_q=5,
        seasonal=seasonal,
        m=m,
        d=None,  # Auto-detect differencing
        trace=True,
        error_action='ignore',
        suppress_warnings=True,
        stepwise=True
    )

    forecast = model.predict(n_periods=30)

    return {
        'model': model,
        'forecast': forecast,
        'order': model.order,
        'seasonal_order': model.seasonal_order,
        'aic': model.aic()
    }
```

### 2.4 Prophet (Facebook)

**When to Use**:
- Strong seasonal patterns (daily, weekly, yearly)
- Holidays and special events
- Missing data
- Trend changes
- Non-technical stakeholders (interpretable)

**Basic Usage**:
```python
from prophet import Prophet
import pandas as pd

def prophet_forecast(dates, values, periods=90, holidays=None):
    """
    Facebook Prophet forecasting.

    Args:
        dates: Array of dates
        values: Array of values
        periods: Days to forecast
        holidays: DataFrame with holiday dates
    """
    # Prepare data
    df = pd.DataFrame({
        'ds': pd.to_datetime(dates),
        'y': values
    })

    # Initialize model
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        holidays=holidays
    )

    # Fit
    model.fit(df)

    # Make future dataframe
    future = model.make_future_dataframe(periods=periods)

    # Forecast
    forecast = model.predict(future)

    return {
        'forecast': forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']],
        'components': model.plot_components(forecast),
        'model': model
    }

# Example with holidays
import pandas as pd

holidays = pd.DataFrame({
    'holiday': 'black_friday',
    'ds': pd.to_datetime(['2024-11-29', '2025-11-28']),
    'lower_window': -1,
    'upper_window': 1
})

dates = pd.date_range('2024-01-01', '2024-10-29', freq='D')
traffic = np.array([...])  # Daily traffic

result = prophet_forecast(dates, traffic, periods=90, holidays=holidays)
```

**Advanced Prophet Configuration**:
```python
def advanced_prophet_forecast(df, forecast_days=90):
    """Prophet with custom configuration."""
    model = Prophet(
        # Trend
        growth='linear',  # or 'logistic' for saturating growth
        changepoint_prior_scale=0.05,  # Flexibility of trend changes
        changepoint_range=0.8,  # Fit changepoints on first 80%

        # Seasonality
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        seasonality_mode='multiplicative',  # or 'additive'
        seasonality_prior_scale=10.0,

        # Uncertainty
        interval_width=0.95,

        # Holidays
        holidays_prior_scale=10.0
    )

    # Add custom seasonality
    model.add_seasonality(
        name='monthly',
        period=30.5,
        fourier_order=5
    )

    # Add country-specific holidays
    model.add_country_holidays(country_name='US')

    # Fit
    model.fit(df)

    # Forecast
    future = model.make_future_dataframe(periods=forecast_days)
    forecast = model.predict(future)

    return model, forecast
```

### 2.5 LSTM Neural Networks

**When to Use**:
- Complex non-linear patterns
- Multiple input features
- Long sequences
- When accuracy is critical and compute is available

**Implementation**:
```python
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from sklearn.preprocessing import MinMaxScaler

def prepare_lstm_data(data, lookback=30):
    """Prepare data for LSTM training."""
    scaler = MinMaxScaler()
    scaled_data = scaler.fit_transform(data.reshape(-1, 1))

    X, y = [], []
    for i in range(lookback, len(scaled_data)):
        X.append(scaled_data[i-lookback:i, 0])
        y.append(scaled_data[i, 0])

    X = np.array(X)
    y = np.array(y)
    X = X.reshape(X.shape[0], X.shape[1], 1)

    return X, y, scaler

def build_lstm_model(lookback, units=50):
    """Build LSTM model for time series forecasting."""
    model = Sequential([
        LSTM(units=units, return_sequences=True, input_shape=(lookback, 1)),
        Dropout(0.2),
        LSTM(units=units, return_sequences=False),
        Dropout(0.2),
        Dense(units=25),
        Dense(units=1)
    ])

    model.compile(optimizer='adam', loss='mse', metrics=['mae'])

    return model

def lstm_forecast(data, lookback=30, periods_ahead=30, epochs=50):
    """
    LSTM-based forecasting.

    Args:
        data: Historical time series
        lookback: Number of past periods to use
        periods_ahead: Forecast horizon
        epochs: Training epochs
    """
    # Prepare data
    X, y, scaler = prepare_lstm_data(data, lookback=lookback)

    # Split train/validation
    split = int(0.8 * len(X))
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    # Build and train model
    model = build_lstm_model(lookback)

    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=epochs,
        batch_size=32,
        verbose=0
    )

    # Forecast
    forecast = []
    current_sequence = data[-lookback:].reshape(-1, 1)
    current_sequence = scaler.transform(current_sequence)

    for _ in range(periods_ahead):
        # Predict next value
        X_pred = current_sequence[-lookback:].reshape(1, lookback, 1)
        next_val = model.predict(X_pred, verbose=0)[0, 0]

        # Append to sequence
        forecast.append(next_val)
        current_sequence = np.append(current_sequence, [[next_val]], axis=0)

    # Inverse transform
    forecast = scaler.inverse_transform(np.array(forecast).reshape(-1, 1))

    return {
        'forecast': forecast.flatten(),
        'model': model,
        'history': history.history,
        'scaler': scaler
    }
```

### 2.6 Multi-variate Forecasting

**When to Use**:
- Multiple correlated metrics
- External factors influence capacity
- Complex systems with interdependencies

**Vector Autoregression (VAR)**:
```python
from statsmodels.tsa.api import VAR

def multivariate_forecast(data_dict, periods_ahead=30):
    """
    Forecast multiple time series simultaneously.

    Args:
        data_dict: Dictionary of series {'cpu': [...], 'memory': [...]}
        periods_ahead: Forecast horizon
    """
    # Prepare data
    df = pd.DataFrame(data_dict)

    # Fit VAR model
    model = VAR(df)
    fitted = model.fit(maxlags=15, ic='aic')

    # Forecast
    forecast = fitted.forecast(df.values[-fitted.k_ar:], steps=periods_ahead)

    # Convert to dataframe
    forecast_df = pd.DataFrame(
        forecast,
        columns=df.columns
    )

    return {
        'forecast': forecast_df,
        'summary': fitted.summary(),
        'order': fitted.k_ar
    }

# Example
data = {
    'cpu_usage': cpu_data,
    'memory_usage': memory_data,
    'disk_io': disk_data,
    'network_traffic': network_data
}

result = multivariate_forecast(data, periods_ahead=60)
```

### 2.7 Scenario-Based Forecasting

**Multiple Scenarios**:
```python
def scenario_forecast(data, growth_scenarios):
    """
    Generate forecasts for multiple scenarios.

    Args:
        data: Historical time series
        growth_scenarios: Dict of scenarios with growth rates
            e.g., {'conservative': 0.02, 'expected': 0.05, 'aggressive': 0.10}
    """
    results = {}

    baseline = data[-1]
    periods = 90

    for scenario_name, growth_rate in growth_scenarios.items():
        # Compound growth
        forecast = []
        current = baseline

        for i in range(periods):
            current = current * (1 + growth_rate / 30)  # Daily growth
            forecast.append(current)

        results[scenario_name] = np.array(forecast)

    return results

# Example
scenarios = {
    'conservative': 0.02,  # 2% monthly growth
    'expected': 0.05,      # 5% monthly growth
    'aggressive': 0.10     # 10% monthly growth
}

forecasts = scenario_forecast(cpu_usage, scenarios)
```

### 2.8 Forecast Evaluation

**Metrics**:
```python
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

def evaluate_forecast(actual, predicted):
    """Calculate forecast accuracy metrics."""
    mae = mean_absolute_error(actual, predicted)
    mse = mean_squared_error(actual, predicted)
    rmse = np.sqrt(mse)
    mape = np.mean(np.abs((actual - predicted) / actual)) * 100
    r2 = r2_score(actual, predicted)

    return {
        'mae': mae,
        'mse': mse,
        'rmse': rmse,
        'mape': mape,  # Mean Absolute Percentage Error
        'r2': r2
    }

# Backtesting
def backtest_forecast(data, forecast_func, train_size=0.8):
    """Backtest a forecasting function."""
    split = int(len(data) * train_size)
    train = data[:split]
    test = data[split:]

    forecast = forecast_func(train, periods_ahead=len(test))

    metrics = evaluate_forecast(test, forecast)

    return {
        'metrics': metrics,
        'train': train,
        'test': test,
        'forecast': forecast
    }
```

---

## 3. Resource Modeling

### 3.1 CPU Modeling

**Basic CPU Model**:
```
CPU_needed = (requests_per_second × cpu_time_per_request) / (cores_per_instance × target_utilization)

Example:
- 1,000 req/s
- 10ms CPU per request
- 4 cores per instance
- 70% target utilization

CPU_needed = (1000 × 0.010) / (4 × 0.70)
           = 10 / 2.8
           = 3.57 cores

Need at least 1 instance (4 cores)
```

**Per-Request CPU Model**:
```python
def calculate_cpu_capacity(
    requests_per_second: float,
    cpu_ms_per_request: float,
    cores_per_instance: int,
    target_utilization: float = 0.70
) -> dict:
    """
    Calculate CPU capacity requirements.

    Returns:
        Dictionary with capacity calculations
    """
    # Total CPU time needed per second
    total_cpu_seconds = (requests_per_second * cpu_ms_per_request) / 1000

    # CPU capacity per instance
    capacity_per_instance = cores_per_instance * target_utilization

    # Instances needed
    instances_needed = total_cpu_seconds / capacity_per_instance

    # Requests per instance
    requests_per_instance = requests_per_second / instances_needed

    return {
        'total_cpu_seconds_needed': total_cpu_seconds,
        'instances_needed': np.ceil(instances_needed),
        'requests_per_instance': requests_per_instance,
        'cpu_utilization': (total_cpu_seconds / (cores_per_instance * instances_needed)) * 100
    }

# Example
result = calculate_cpu_capacity(
    requests_per_second=5000,
    cpu_ms_per_request=15,
    cores_per_instance=8,
    target_utilization=0.70
)
```

**CPU with Concurrency**:
```python
def calculate_cpu_with_concurrency(
    requests_per_second: float,
    avg_response_time_ms: float,
    cores_per_instance: int,
    target_utilization: float = 0.70
) -> dict:
    """Calculate CPU using Little's Law for concurrency."""
    # Concurrent requests (Little's Law)
    concurrent_requests = requests_per_second * (avg_response_time_ms / 1000)

    # CPU capacity
    available_capacity = cores_per_instance * target_utilization

    # Instances needed
    instances_needed = concurrent_requests / available_capacity

    return {
        'concurrent_requests': concurrent_requests,
        'instances_needed': np.ceil(instances_needed),
        'requests_per_core': requests_per_second / (cores_per_instance * instances_needed)
    }
```

### 3.2 Memory Modeling

**Basic Memory Model**:
```
Memory = base_memory + (connections × memory_per_connection) + (cache_size) + headroom

Example:
- Base: 500 MB
- 1,000 connections
- 2 MB per connection
- Cache: 1 GB
- 20% headroom

Memory = 500 + (1000 × 2) + 1000
       = 3,500 MB
       = 3.5 GB

With headroom: 3.5 × 1.2 = 4.2 GB
Select instance: 8 GB RAM
```

**Detailed Memory Model**:
```python
def calculate_memory_requirements(
    base_memory_mb: float,
    concurrent_connections: int,
    memory_per_connection_mb: float,
    cache_size_mb: float = 0,
    heap_size_mb: float = 0,
    buffer_size_mb: float = 0,
    headroom: float = 0.20
) -> dict:
    """
    Calculate memory requirements with headroom.

    Returns:
        Memory breakdown and requirements
    """
    # Component memory
    connection_memory = concurrent_connections * memory_per_connection_mb

    # Total without headroom
    total_memory = (
        base_memory_mb +
        connection_memory +
        cache_size_mb +
        heap_size_mb +
        buffer_size_mb
    )

    # With headroom
    total_with_headroom = total_memory * (1 + headroom)

    return {
        'base_memory_mb': base_memory_mb,
        'connection_memory_mb': connection_memory,
        'cache_memory_mb': cache_size_mb,
        'heap_memory_mb': heap_size_mb,
        'buffer_memory_mb': buffer_size_mb,
        'total_memory_mb': total_memory,
        'headroom_mb': total_memory * headroom,
        'total_with_headroom_mb': total_with_headroom,
        'total_with_headroom_gb': total_with_headroom / 1024
    }

# Example: Web application
memory_calc = calculate_memory_requirements(
    base_memory_mb=512,
    concurrent_connections=5000,
    memory_per_connection_mb=1.5,
    cache_size_mb=2048,
    heap_size_mb=1024,
    buffer_size_mb=512,
    headroom=0.20
)
```

**Garbage Collection Overhead**:
```python
def calculate_memory_with_gc(
    application_memory_mb: float,
    gc_algorithm: str = 'g1gc',
    heap_utilization_target: float = 0.70
) -> dict:
    """
    Calculate memory accounting for garbage collection.

    Args:
        application_memory_mb: Memory used by application
        gc_algorithm: GC algorithm (g1gc, zgc, shenandoah)
        heap_utilization_target: Target heap utilization
    """
    # GC overhead varies by algorithm
    gc_overhead = {
        'g1gc': 0.25,        # 25% overhead
        'zgc': 0.10,         # 10% overhead
        'shenandoah': 0.15,  # 15% overhead
        'parallel': 0.20     # 20% overhead
    }

    overhead = gc_overhead.get(gc_algorithm, 0.25)

    # Calculate heap size
    heap_size = application_memory_mb / heap_utilization_target

    # Total memory with GC overhead
    total_memory = heap_size * (1 + overhead)

    return {
        'application_memory_mb': application_memory_mb,
        'heap_size_mb': heap_size,
        'gc_overhead_mb': heap_size * overhead,
        'total_memory_mb': total_memory,
        'gc_algorithm': gc_algorithm
    }
```

### 3.3 Storage Modeling

**Growth-Based Storage Model**:
```
Storage = current_size + (daily_growth × forecast_days) + (daily_growth × retention_days)

Example:
- Current: 1 TB
- Growth: 10 GB/day
- Forecast: 180 days
- Retention: 90 days

Storage = 1000 + (10 × 180) + (10 × 90)
        = 1000 + 1800 + 900
        = 3,700 GB
        = 3.7 TB

With 20% safety margin: 4.4 TB
```

**Storage Modeling Function**:
```python
def calculate_storage_requirements(
    current_storage_gb: float,
    daily_growth_gb: float,
    forecast_days: int = 180,
    retention_days: int = 90,
    safety_margin: float = 0.20,
    storage_type: str = 'ssd'
) -> dict:
    """
    Calculate storage capacity requirements.

    Args:
        current_storage_gb: Current storage usage
        daily_growth_gb: Daily growth rate
        forecast_days: Planning horizon
        retention_days: Data retention period
        safety_margin: Safety margin percentage
        storage_type: ssd, hdd, or archive
    """
    # Calculate growth
    forecast_growth = daily_growth_gb * forecast_days
    retention_size = daily_growth_gb * retention_days

    # Total without margin
    total_storage = current_storage_gb + forecast_growth

    # With safety margin
    total_with_margin = total_storage * (1 + safety_margin)

    # Cost estimation (rough)
    cost_per_gb = {
        'ssd': 0.10,      # $0.10/GB/month
        'hdd': 0.03,      # $0.03/GB/month
        'archive': 0.004  # $0.004/GB/month
    }

    monthly_cost = total_with_margin * cost_per_gb.get(storage_type, 0.10)

    return {
        'current_storage_gb': current_storage_gb,
        'forecast_growth_gb': forecast_growth,
        'total_storage_gb': total_storage,
        'safety_margin_gb': total_storage * safety_margin,
        'total_with_margin_gb': total_with_margin,
        'total_with_margin_tb': total_with_margin / 1024,
        'storage_type': storage_type,
        'estimated_monthly_cost': monthly_cost
    }
```

**IOPS Modeling**:
```python
def calculate_iops_requirements(
    reads_per_second: float,
    writes_per_second: float,
    read_io_size_kb: float = 4,
    write_io_size_kb: float = 4,
    target_latency_ms: float = 10
) -> dict:
    """
    Calculate IOPS requirements.

    Returns:
        IOPS and throughput requirements
    """
    total_iops = reads_per_second + writes_per_second

    # Throughput (MB/s)
    read_throughput = (reads_per_second * read_io_size_kb) / 1024
    write_throughput = (writes_per_second * write_io_size_kb) / 1024
    total_throughput = read_throughput + write_throughput

    # Recommend storage type
    if total_iops < 3000 and target_latency_ms > 20:
        storage_type = 'HDD (7200 RPM)'
        iops_per_disk = 100
    elif total_iops < 16000:
        storage_type = 'SSD (SATA)'
        iops_per_disk = 80000
    else:
        storage_type = 'NVMe SSD'
        iops_per_disk = 500000

    return {
        'total_iops': total_iops,
        'read_iops': reads_per_second,
        'write_iops': writes_per_second,
        'read_throughput_mbs': read_throughput,
        'write_throughput_mbs': write_throughput,
        'total_throughput_mbs': total_throughput,
        'recommended_storage': storage_type,
        'target_latency_ms': target_latency_ms
    }
```

### 3.4 Network Modeling

**Bandwidth Calculation**:
```
Bandwidth = (requests_per_second × avg_response_size_bytes × 8) / (1000 * 1000)

Example:
- 10,000 req/s
- 50 KB average response

Bandwidth = (10000 × 50000 × 8) / 1000000
          = 4,000,000,000 / 1000000
          = 4,000 Mbps
          = 4 Gbps

Peak (3x average): 12 Gbps
```

**Network Capacity Model**:
```python
def calculate_network_requirements(
    requests_per_second: float,
    avg_request_size_bytes: float,
    avg_response_size_bytes: float,
    peak_multiplier: float = 3.0,
    overhead: float = 0.10
) -> dict:
    """
    Calculate network bandwidth requirements.

    Returns:
        Bandwidth requirements in Mbps and Gbps
    """
    # Calculate traffic
    ingress_bytes_per_sec = requests_per_second * avg_request_size_bytes
    egress_bytes_per_sec = requests_per_second * avg_response_size_bytes

    # Convert to bits per second
    ingress_bps = ingress_bytes_per_sec * 8
    egress_bps = egress_bytes_per_sec * 8

    # Convert to Mbps
    ingress_mbps = ingress_bps / (1000 * 1000)
    egress_mbps = egress_bps / (1000 * 1000)

    # Add overhead (TCP, TLS, etc.)
    ingress_mbps_with_overhead = ingress_mbps * (1 + overhead)
    egress_mbps_with_overhead = egress_mbps * (1 + overhead)

    # Peak traffic
    peak_ingress = ingress_mbps_with_overhead * peak_multiplier
    peak_egress = egress_mbps_with_overhead * peak_multiplier

    return {
        'avg_ingress_mbps': ingress_mbps_with_overhead,
        'avg_egress_mbps': egress_mbps_with_overhead,
        'peak_ingress_mbps': peak_ingress,
        'peak_egress_mbps': peak_egress,
        'peak_ingress_gbps': peak_ingress / 1000,
        'peak_egress_gbps': peak_egress / 1000,
        'recommended_capacity_gbps': np.ceil(max(peak_ingress, peak_egress) / 1000)
    }

# Example
network = calculate_network_requirements(
    requests_per_second=15000,
    avg_request_size_bytes=2048,   # 2 KB
    avg_response_size_bytes=51200,  # 50 KB
    peak_multiplier=4.0
)
```

**Connection Capacity**:
```python
def calculate_connection_capacity(
    concurrent_connections: int,
    avg_connection_duration_seconds: float,
    new_connections_per_second: float,
    time_wait_seconds: float = 60
) -> dict:
    """
    Calculate connection handling capacity.

    Args:
        concurrent_connections: Max concurrent connections
        avg_connection_duration_seconds: How long connections stay open
        new_connections_per_second: Rate of new connections
        time_wait_seconds: TIME_WAIT duration
    """
    # Connection states
    active_connections = concurrent_connections
    time_wait_connections = new_connections_per_second * time_wait_seconds
    total_connections = active_connections + time_wait_connections

    # Port exhaustion risk (65535 ephemeral ports)
    port_utilization = (total_connections / 65535) * 100

    return {
        'active_connections': active_connections,
        'time_wait_connections': time_wait_connections,
        'total_connection_states': total_connections,
        'port_utilization_percent': port_utilization,
        'risk_of_port_exhaustion': port_utilization > 80
    }
```

---

## 4. Load Testing

### 4.1 Load Testing Strategy

**Test Types**:

1. **Baseline Test**: Establish performance baseline with normal load
2. **Load Test**: Validate capacity at expected peak load
3. **Stress Test**: Find breaking point by exceeding capacity
4. **Soak Test**: Detect memory leaks and resource exhaustion over time
5. **Spike Test**: Validate auto-scaling and recovery from sudden load
6. **Scalability Test**: Measure performance as load increases

### 4.2 Locust Load Testing

**Basic Locust Test**:
```python
from locust import HttpUser, task, between, events
import random

class APIUser(HttpUser):
    """Simulate API user behavior."""

    wait_time = between(1, 3)  # Think time between requests

    def on_start(self):
        """Login or setup before tests."""
        response = self.client.post("/api/login", json={
            "username": f"user_{random.randint(1, 10000)}",
            "password": "test"
        })
        self.token = response.json().get("token")

    @task(3)  # Weight: 3x more likely than other tasks
    def get_items(self):
        """GET /api/items - Most common operation."""
        headers = {"Authorization": f"Bearer {self.token}"}
        self.client.get("/api/items", headers=headers, name="GET /items")

    @task(2)
    def get_item_detail(self):
        """GET /api/items/:id"""
        item_id = random.randint(1, 1000)
        headers = {"Authorization": f"Bearer {self.token}"}
        self.client.get(
            f"/api/items/{item_id}",
            headers=headers,
            name="GET /items/:id"
        )

    @task(1)
    def create_item(self):
        """POST /api/items"""
        headers = {"Authorization": f"Bearer {self.token}"}
        self.client.post(
            "/api/items",
            json={
                "name": f"Item {random.randint(1, 10000)}",
                "description": "Test item",
                "price": random.uniform(10, 1000)
            },
            headers=headers,
            name="POST /items"
        )

# Run: locust -f loadtest.py --users 1000 --spawn-rate 10 --run-time 30m
```

**Advanced Locust with Custom Metrics**:
```python
from locust import HttpUser, task, between, events
import time

# Custom metric tracking
request_latencies = []

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Track custom metrics."""
    if exception is None:
        request_latencies.append(response_time)

class AdvancedAPIUser(HttpUser):
    """Advanced load test with realistic patterns."""

    wait_time = between(0.5, 2)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_start = time.time()

    @task
    def realistic_user_session(self):
        """Simulate realistic user session."""
        # Browse items
        self.client.get("/api/items?page=1")
        time.sleep(random.uniform(1, 3))

        # View item details
        item_id = random.randint(1, 100)
        self.client.get(f"/api/items/{item_id}")
        time.sleep(random.uniform(2, 5))

        # Add to cart (50% probability)
        if random.random() < 0.5:
            self.client.post("/api/cart", json={"item_id": item_id})
            time.sleep(random.uniform(1, 2))

            # Checkout (30% probability)
            if random.random() < 0.3:
                self.client.post("/api/checkout", json={
                    "payment_method": "card"
                })

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Report custom metrics at end of test."""
    if request_latencies:
        print(f"\n=== Custom Metrics ===")
        print(f"P50 latency: {np.percentile(request_latencies, 50):.2f}ms")
        print(f"P95 latency: {np.percentile(request_latencies, 95):.2f}ms")
        print(f"P99 latency: {np.percentile(request_latencies, 99):.2f}ms")
```

**Distributed Locust**:
```bash
# Master node
locust -f loadtest.py --master --expect-workers 4

# Worker nodes (run on 4 machines)
locust -f loadtest.py --worker --master-host=<master-ip>

# Or use Kubernetes
kubectl apply -f locust-master.yaml
kubectl apply -f locust-workers.yaml
```

### 4.3 k6 Load Testing

**Basic k6 Script**:
```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const itemLatency = new Trend('item_latency');

// Load test configuration
export const options = {
  stages: [
    { duration: '2m', target: 100 },   // Ramp up to 100 users
    { duration: '5m', target: 100 },   // Stay at 100 users
    { duration: '2m', target: 500 },   // Ramp to 500 users
    { duration: '5m', target: 500 },   // Stay at 500 users
    { duration: '2m', target: 0 },     // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% of requests under 500ms
    http_req_failed: ['rate<0.01'],    // Error rate < 1%
    errors: ['rate<0.05'],             // Custom error rate < 5%
  },
};

export default function () {
  // Login
  const loginRes = http.post('https://api.example.com/login', JSON.stringify({
    username: 'testuser',
    password: 'testpass',
  }), {
    headers: { 'Content-Type': 'application/json' },
  });

  check(loginRes, {
    'login successful': (r) => r.status === 200,
  });

  const token = loginRes.json('token');

  // Get items
  const itemsRes = http.get('https://api.example.com/items', {
    headers: { 'Authorization': `Bearer ${token}` },
  });

  const success = check(itemsRes, {
    'items retrieved': (r) => r.status === 200,
    'response time OK': (r) => r.timings.duration < 1000,
  });

  errorRate.add(!success);
  itemLatency.add(itemsRes.timings.duration);

  sleep(1);
}

// Run: k6 run loadtest.js
```

**Scenario-Based k6**:
```javascript
import http from 'k6/http';
import { check, sleep, group } from 'k6';

export const options = {
  scenarios: {
    // Constant load
    constant_load: {
      executor: 'constant-vus',
      vus: 100,
      duration: '10m',
      exec: 'constantLoad',
    },

    // Ramping load
    ramping_load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '5m', target: 500 },
        { duration: '10m', target: 500 },
        { duration: '5m', target: 0 },
      ],
      exec: 'rampingLoad',
      startTime: '10m',  // Start after constant load
    },

    // Spike test
    spike_test: {
      executor: 'constant-arrival-rate',
      rate: 1000,        // 1000 requests per timeUnit
      timeUnit: '1s',
      duration: '2m',
      preAllocatedVUs: 100,
      maxVUs: 1000,
      exec: 'spikeTest',
      startTime: '20m',
    },
  },
  thresholds: {
    http_req_duration: ['p(99)<1000'],
    http_req_failed: ['rate<0.01'],
  },
};

export function constantLoad() {
  group('API Browse Flow', function () {
    http.get('https://api.example.com/items');
    sleep(2);
    http.get('https://api.example.com/items/1');
    sleep(3);
  });
}

export function rampingLoad() {
  http.post('https://api.example.com/items', JSON.stringify({
    name: 'Test Item',
  }));
  sleep(1);
}

export function spikeTest() {
  http.get('https://api.example.com/health');
}
```

### 4.4 Load Test Analysis

**Analyzing Results**:
```python
def analyze_load_test_results(metrics_file: str):
    """
    Analyze load test results from k6 JSON output.

    Args:
        metrics_file: Path to k6 JSON output
    """
    with open(metrics_file) as f:
        data = json.load(f)

    metrics = data['metrics']

    # Extract key metrics
    http_req_duration = metrics['http_req_duration']
    http_req_failed = metrics['http_req_failed']
    iterations = metrics['iterations']

    analysis = {
        'throughput': {
            'total_requests': http_req_duration['count'],
            'requests_per_second': http_req_duration['rate'],
            'failed_requests': http_req_failed['count'],
            'error_rate_percent': http_req_failed['rate'] * 100,
        },
        'latency': {
            'p50_ms': http_req_duration['p(50)'],
            'p95_ms': http_req_duration['p(95)'],
            'p99_ms': http_req_duration['p(99)'],
            'max_ms': http_req_duration['max'],
            'avg_ms': http_req_duration['avg'],
        },
        'capacity_assessment': {},
    }

    # Assess capacity
    if http_req_failed['rate'] < 0.01 and http_req_duration['p(95)'] < 500:
        analysis['capacity_assessment']['status'] = 'PASS'
        analysis['capacity_assessment']['message'] = 'System handled load successfully'
    elif http_req_failed['rate'] < 0.05:
        analysis['capacity_assessment']['status'] = 'WARNING'
        analysis['capacity_assessment']['message'] = 'System degraded under load'
    else:
        analysis['capacity_assessment']['status'] = 'FAIL'
        analysis['capacity_assessment']['message'] = 'System failed under load'

    return analysis
```

---

## 5. Scaling Strategies

### 5.1 Vertical vs Horizontal Scaling

**Vertical Scaling (Scale Up)**:
- Add more resources to existing instances
- Increase CPU, memory, disk
- Simpler architecture
- Limited by hardware maximums
- Downtime often required
- Single point of failure

**Horizontal Scaling (Scale Out)**:
- Add more instances
- Distribute load across instances
- Better fault tolerance
- Potentially unlimited scaling
- Requires distributed architecture
- More complex operations

**Decision Matrix**:
```
Use Vertical Scaling When:
├─ Application can't scale horizontally (single-threaded, stateful)
├─ Quick fix needed (< 1 hour)
├─ Cost of refactoring > cost of bigger instance
├─ Working set fits in single machine
└─ Simplified operations preferred

Use Horizontal Scaling When:
├─ Application is stateless or supports sharding
├─ Need fault tolerance (N+1, N+2)
├─ Load varies significantly (benefit from auto-scaling)
├─ Working set exceeds single machine
└─ Long-term scalability required
```

### 5.2 Auto-Scaling Strategies

**Target Tracking Scaling**:
```python
def calculate_target_tracking_scaling(
    current_metric_value: float,
    target_value: float,
    current_instances: int,
    min_instances: int = 1,
    max_instances: int = 100
) -> dict:
    """
    Calculate desired instance count for target tracking.

    Example:
        Current CPU: 80%
        Target CPU: 70%
        Current instances: 10

        Desired = 10 × (80/70) = 11.4 → 12 instances
    """
    # Calculate desired capacity
    desired_instances = current_instances * (current_metric_value / target_value)

    # Apply bounds
    desired_instances = max(min_instances, min(max_instances, desired_instances))
    desired_instances = int(np.ceil(desired_instances))

    # Calculate change
    change = desired_instances - current_instances

    return {
        'current_instances': current_instances,
        'desired_instances': desired_instances,
        'change': change,
        'action': 'scale_out' if change > 0 else 'scale_in' if change < 0 else 'no_change',
        'current_metric': current_metric_value,
        'target_metric': target_value
    }
```

**Step Scaling**:
```python
def calculate_step_scaling(
    current_metric_value: float,
    current_instances: int,
    step_adjustments: list
) -> dict:
    """
    Calculate scaling based on step adjustments.

    Args:
        current_metric_value: Current metric value
        current_instances: Current instance count
        step_adjustments: List of dicts with 'lower_bound', 'upper_bound', 'adjustment'

    Example:
        step_adjustments = [
            {'lower_bound': 70, 'upper_bound': 80, 'adjustment': 1},
            {'lower_bound': 80, 'upper_bound': 90, 'adjustment': 2},
            {'lower_bound': 90, 'upper_bound': None, 'adjustment': 5},
        ]
    """
    adjustment = 0

    for step in step_adjustments:
        lower = step.get('lower_bound', float('-inf'))
        upper = step.get('upper_bound', float('inf'))

        if lower <= current_metric_value < upper:
            adjustment = step['adjustment']
            break

    desired_instances = current_instances + adjustment

    return {
        'current_instances': current_instances,
        'desired_instances': desired_instances,
        'adjustment': adjustment,
        'current_metric': current_metric_value
    }
```

**Predictive Scaling**:
```python
def predictive_scaling(
    forecast: np.ndarray,
    current_capacity: int,
    target_utilization: float = 0.70,
    scale_up_threshold: float = 0.80,
    scale_down_threshold: float = 0.50,
    lookahead_minutes: int = 15
) -> dict:
    """
    Scale based on forecasted load.

    Args:
        forecast: Array of predicted load values
        current_capacity: Current capacity (e.g., instances)
        target_utilization: Target utilization percentage
        lookahead_minutes: How far ahead to look
    """
    # Look ahead
    future_load = forecast[:lookahead_minutes]
    max_future_load = np.max(future_load)

    # Calculate required capacity
    required_capacity = max_future_load / target_utilization

    # Calculate current utilization
    current_load = forecast[0]
    current_utilization = current_load / current_capacity

    # Scaling decision
    if current_utilization > scale_up_threshold:
        action = 'scale_up_now'
        desired_capacity = int(np.ceil(required_capacity * 1.2))  # 20% buffer
    elif current_utilization < scale_down_threshold:
        action = 'scale_down'
        desired_capacity = int(np.ceil(required_capacity))
    elif required_capacity > current_capacity:
        action = 'scale_up_proactive'
        desired_capacity = int(np.ceil(required_capacity))
    else:
        action = 'no_change'
        desired_capacity = current_capacity

    return {
        'current_capacity': current_capacity,
        'desired_capacity': desired_capacity,
        'current_utilization': current_utilization,
        'predicted_max_load': max_future_load,
        'required_capacity': required_capacity,
        'action': action
    }
```

### 5.3 Kubernetes Horizontal Pod Autoscaler (HPA)

**Comprehensive HPA Configuration**:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api

  minReplicas: 3
  maxReplicas: 50

  metrics:
    # CPU-based scaling
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70

    # Memory-based scaling
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80

    # Custom metric: Requests per second per pod
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "100"

    # External metric: SQS queue depth
    - type: External
      external:
        metric:
          name: sqs_queue_depth
          selector:
            matchLabels:
              queue: "orders"
        target:
          type: AverageValue
          averageValue: "30"

  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300  # Wait 5 min before scale down
      policies:
        - type: Percent
          value: 50              # Remove max 50% of pods
          periodSeconds: 60
        - type: Pods
          value: 2               # Remove max 2 pods
          periodSeconds: 60
      selectPolicy: Min          # Use minimum of policies

    scaleUp:
      stabilizationWindowSeconds: 0    # Scale up immediately
      policies:
        - type: Percent
          value: 100             # Double pods
          periodSeconds: 30
        - type: Pods
          value: 5               # Add max 5 pods
          periodSeconds: 30
      selectPolicy: Max          # Use maximum of policies
```

**Vertical Pod Autoscaler (VPA)**:
```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: api-vpa
  namespace: production
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api

  updatePolicy:
    updateMode: "Auto"  # or "Off", "Initial", "Recreate"

  resourcePolicy:
    containerPolicies:
      - containerName: api
        minAllowed:
          cpu: 100m
          memory: 256Mi
        maxAllowed:
          cpu: 2000m
          memory: 4Gi
        controlledResources: ["cpu", "memory"]
        mode: Auto
```

### 5.4 AWS Auto Scaling

**EC2 Auto Scaling with Target Tracking**:
```json
{
  "AutoScalingGroupName": "api-asg",
  "MinSize": 3,
  "MaxSize": 20,
  "DesiredCapacity": 5,
  "DefaultCooldown": 300,
  "HealthCheckType": "ELB",
  "HealthCheckGracePeriod": 300,
  "TargetGroupARNs": ["arn:aws:elasticloadbalancing:..."],
  "Tags": [
    {
      "Key": "Name",
      "Value": "api-server",
      "PropagateAtLaunch": true
    }
  ]
}
```

**Target Tracking Policy**:
```json
{
  "PolicyName": "target-tracking-cpu",
  "PolicyType": "TargetTrackingScaling",
  "TargetTrackingConfiguration": {
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ASGAverageCPUUtilization"
    },
    "TargetValue": 70.0,
    "ScaleInCooldown": 300,
    "ScaleOutCooldown": 60
  }
}
```

**Step Scaling Policy**:
```json
{
  "PolicyName": "step-scaling-cpu",
  "PolicyType": "StepScaling",
  "AdjustmentType": "PercentChangeInCapacity",
  "MetricAggregationType": "Average",
  "StepAdjustments": [
    {
      "MetricIntervalLowerBound": 0,
      "MetricIntervalUpperBound": 10,
      "ScalingAdjustment": 10
    },
    {
      "MetricIntervalLowerBound": 10,
      "MetricIntervalUpperBound": 20,
      "ScalingAdjustment": 20
    },
    {
      "MetricIntervalLowerBound": 20,
      "ScalingAdjustment": 30
    }
  ],
  "Cooldown": 60
}
```

**ECS Service Auto Scaling**:
```json
{
  "ServiceNamespace": "ecs",
  "ResourceId": "service/production/api",
  "ScalableDimension": "ecs:service:DesiredCount",
  "MinCapacity": 3,
  "MaxCapacity": 20,
  "RoleARN": "arn:aws:iam::...:role/ecsAutoscaleRole",
  "PolicyName": "ecs-target-tracking",
  "PolicyType": "TargetTrackingScaling",
  "TargetTrackingScalingPolicyConfiguration": {
    "TargetValue": 70.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
    },
    "ScaleOutCooldown": 60,
    "ScaleInCooldown": 300
  }
}
```

---

## 6. Cost Optimization

### 6.1 Right-Sizing

**Right-Sizing Analysis**:
```python
def analyze_rightsizing_opportunities(
    instances: list,
    utilization_threshold_low: float = 0.30,
    utilization_threshold_high: float = 0.70
) -> list:
    """
    Identify right-sizing opportunities.

    Args:
        instances: List of dicts with instance details
        utilization_threshold_low: Below this, consider downsizing
        utilization_threshold_high: Above this, consider upsizing

    Returns:
        List of recommendations
    """
    recommendations = []

    for instance in instances:
        instance_type = instance['type']
        cpu_util = instance['avg_cpu_utilization']
        memory_util = instance['avg_memory_utilization']
        monthly_cost = instance['monthly_cost']

        # Under-utilized
        if cpu_util < utilization_threshold_low and memory_util < utilization_threshold_low:
            # Recommend smaller instance (50% cost savings)
            estimated_savings = monthly_cost * 0.50

            recommendations.append({
                'instance_id': instance['id'],
                'current_type': instance_type,
                'action': 'downsize',
                'reason': f'Low utilization (CPU: {cpu_util:.1f}%, Memory: {memory_util:.1f}%)',
                'estimated_monthly_savings': estimated_savings,
                'recommended_type': get_smaller_instance_type(instance_type)
            })

        # Over-utilized
        elif cpu_util > utilization_threshold_high or memory_util > utilization_threshold_high:
            recommendations.append({
                'instance_id': instance['id'],
                'current_type': instance_type,
                'action': 'upsize',
                'reason': f'High utilization (CPU: {cpu_util:.1f}%, Memory: {memory_util:.1f}%)',
                'estimated_monthly_cost': monthly_cost * 1.5,
                'recommended_type': get_larger_instance_type(instance_type)
            })

    return recommendations

def get_smaller_instance_type(current_type: str) -> str:
    """Map to smaller instance type."""
    size_map = {
        't3.2xlarge': 't3.xlarge',
        't3.xlarge': 't3.large',
        't3.large': 't3.medium',
        't3.medium': 't3.small',
        'm5.2xlarge': 'm5.xlarge',
        'm5.xlarge': 'm5.large',
        # ... more mappings
    }
    return size_map.get(current_type, current_type)
```

### 6.2 Reserved Capacity

**Reserved Instance Analysis**:
```python
def analyze_reserved_capacity_opportunities(
    instances: list,
    min_age_days: int = 90,
    ri_discount: float = 0.35
) -> list:
    """
    Identify opportunities for reserved capacity.

    Args:
        instances: List of instance details
        min_age_days: Minimum days running to consider for RI
        ri_discount: Discount for 1-year RI (e.g., 0.35 = 35%)
    """
    recommendations = []

    for instance in instances:
        if instance['age_days'] < min_age_days:
            continue

        if instance['is_reserved']:
            continue

        monthly_cost = instance['monthly_cost']
        estimated_savings = monthly_cost * ri_discount
        annual_savings = estimated_savings * 12

        recommendations.append({
            'instance_id': instance['id'],
            'instance_type': instance['type'],
            'current_monthly_cost': monthly_cost,
            'ri_monthly_cost': monthly_cost * (1 - ri_discount),
            'monthly_savings': estimated_savings,
            'annual_savings': annual_savings,
            'recommendation': f'Purchase 1-year RI for {instance["type"]}',
            'age_days': instance['age_days']
        })

    # Sort by savings
    recommendations.sort(key=lambda x: x['annual_savings'], reverse=True)

    return recommendations
```

### 6.3 Spot/Preemptible Instances

**Spot Instance Strategy**:
```python
def calculate_spot_instance_savings(
    workload_type: str,
    current_monthly_cost: float,
    fault_tolerance: bool
) -> dict:
    """
    Calculate potential savings with spot instances.

    Args:
        workload_type: 'batch', 'stateless_web', 'stateful', 'database'
        current_monthly_cost: Current on-demand cost
        fault_tolerance: Whether workload can handle interruptions
    """
    # Spot pricing (typically 70-90% discount)
    spot_discount = 0.75  # 75% average discount

    # Suitability score
    suitability_scores = {
        'batch': 1.0,           # Perfect for spot
        'stateless_web': 0.8,   # Good with proper handling
        'stateful': 0.3,        # Risky
        'database': 0.1         # Not recommended
    }

    suitability = suitability_scores.get(workload_type, 0.5)

    if not fault_tolerance:
        suitability *= 0.5

    # Calculate savings
    spot_monthly_cost = current_monthly_cost * (1 - spot_discount)
    monthly_savings = current_monthly_cost - spot_monthly_cost

    # Recommendation
    if suitability >= 0.7:
        recommendation = 'Highly recommended'
    elif suitability >= 0.5:
        recommendation = 'Consider with fallback to on-demand'
    else:
        recommendation = 'Not recommended'

    return {
        'workload_type': workload_type,
        'suitability_score': suitability,
        'current_monthly_cost': current_monthly_cost,
        'spot_monthly_cost': spot_monthly_cost,
        'monthly_savings': monthly_savings,
        'annual_savings': monthly_savings * 12,
        'discount_percentage': spot_discount * 100,
        'recommendation': recommendation
    }
```

### 6.4 Storage Tiering

**Storage Lifecycle Policy**:
```python
def design_storage_lifecycle(
    data_age_days: int,
    access_frequency: str,
    data_size_gb: float
) -> dict:
    """
    Recommend storage tier based on access patterns.

    Args:
        data_age_days: Age of data in days
        access_frequency: 'frequent', 'infrequent', 'rare', 'archive'
        data_size_gb: Size in GB
    """
    # Storage tiers and costs (example AWS S3 pricing)
    tiers = {
        's3_standard': {
            'name': 'S3 Standard',
            'cost_per_gb_month': 0.023,
            'use_case': 'Frequently accessed data'
        },
        's3_infrequent': {
            'name': 'S3 Infrequent Access',
            'cost_per_gb_month': 0.0125,
            'use_case': 'Data accessed < 1/month'
        },
        's3_glacier': {
            'name': 'S3 Glacier',
            'cost_per_gb_month': 0.004,
            'use_case': 'Archival data, retrieval in hours'
        },
        's3_deep_archive': {
            'name': 'S3 Glacier Deep Archive',
            'cost_per_gb_month': 0.00099,
            'use_case': 'Long-term archive, retrieval in 12-48 hours'
        }
    }

    # Select tier
    if access_frequency == 'frequent' or data_age_days < 30:
        tier = 's3_standard'
    elif access_frequency == 'infrequent' or data_age_days < 90:
        tier = 's3_infrequent'
    elif access_frequency == 'rare' or data_age_days < 365:
        tier = 's3_glacier'
    else:
        tier = 's3_deep_archive'

    selected_tier = tiers[tier]
    monthly_cost = data_size_gb * selected_tier['cost_per_gb_month']

    # Compare with standard storage
    standard_cost = data_size_gb * tiers['s3_standard']['cost_per_gb_month']
    savings = standard_cost - monthly_cost

    return {
        'recommended_tier': selected_tier['name'],
        'monthly_cost': monthly_cost,
        'standard_storage_cost': standard_cost,
        'monthly_savings': savings,
        'annual_savings': savings * 12,
        'use_case': selected_tier['use_case']
    }
```

**Automated Lifecycle Transition**:
```python
def generate_lifecycle_policy(transitions: list) -> dict:
    """
    Generate S3 lifecycle policy.

    Args:
        transitions: List of dicts with 'days' and 'storage_class'

    Example:
        transitions = [
            {'days': 30, 'storage_class': 'STANDARD_IA'},
            {'days': 90, 'storage_class': 'GLACIER'},
            {'days': 365, 'storage_class': 'DEEP_ARCHIVE'}
        ]
    """
    policy = {
        'Rules': [
            {
                'Id': 'auto-tier-policy',
                'Status': 'Enabled',
                'Prefix': '',  # Apply to all objects
                'Transitions': []
            }
        ]
    }

    for transition in transitions:
        policy['Rules'][0]['Transitions'].append({
            'Days': transition['days'],
            'StorageClass': transition['storage_class']
        })

    # Add expiration if needed
    # policy['Rules'][0]['Expiration'] = {'Days': 730}

    return policy
```

---

## 7. Cloud Resource Planning

### 7.1 AWS Capacity Planning

**EC2 Instance Selection**:
```python
def select_ec2_instance(
    cpu_required: float,
    memory_required_gb: float,
    network_performance: str = 'moderate',
    storage_type: str = 'ebs'
) -> dict:
    """
    Recommend EC2 instance type.

    Args:
        cpu_required: vCPUs needed
        memory_required_gb: Memory in GB
        network_performance: 'low', 'moderate', 'high', 'very_high'
        storage_type: 'ebs', 'instance_store'
    """
    # Simplified instance type database
    instance_types = [
        {'type': 't3.small', 'vcpu': 2, 'memory_gb': 2, 'network': 'low', 'cost_hour': 0.0208},
        {'type': 't3.medium', 'vcpu': 2, 'memory_gb': 4, 'network': 'low', 'cost_hour': 0.0416},
        {'type': 't3.large', 'vcpu': 2, 'memory_gb': 8, 'network': 'moderate', 'cost_hour': 0.0832},
        {'type': 'm5.large', 'vcpu': 2, 'memory_gb': 8, 'network': 'moderate', 'cost_hour': 0.096},
        {'type': 'm5.xlarge', 'vcpu': 4, 'memory_gb': 16, 'network': 'moderate', 'cost_hour': 0.192},
        {'type': 'm5.2xlarge', 'vcpu': 8, 'memory_gb': 32, 'network': 'high', 'cost_hour': 0.384},
        {'type': 'c5.xlarge', 'vcpu': 4, 'memory_gb': 8, 'network': 'high', 'cost_hour': 0.17},
        {'type': 'c5.2xlarge', 'vcpu': 8, 'memory_gb': 16, 'network': 'high', 'cost_hour': 0.34},
        {'type': 'r5.large', 'vcpu': 2, 'memory_gb': 16, 'network': 'moderate', 'cost_hour': 0.126},
        {'type': 'r5.xlarge', 'vcpu': 4, 'memory_gb': 32, 'network': 'high', 'cost_hour': 0.252},
    ]

    # Filter by requirements
    suitable = []
    for inst in instance_types:
        if inst['vcpu'] >= cpu_required and inst['memory_gb'] >= memory_required_gb:
            suitable.append(inst)

    if not suitable:
        return {'error': 'No suitable instance type found'}

    # Sort by cost (cheapest first)
    suitable.sort(key=lambda x: x['cost_hour'])

    recommended = suitable[0]

    return {
        'recommended_type': recommended['type'],
        'vcpu': recommended['vcpu'],
        'memory_gb': recommended['memory_gb'],
        'hourly_cost': recommended['cost_hour'],
        'monthly_cost': recommended['cost_hour'] * 730,
        'annual_cost': recommended['cost_hour'] * 730 * 12
    }
```

**RDS Capacity Planning**:
```python
def plan_rds_capacity(
    connections: int,
    storage_gb: int,
    iops_required: int,
    multi_az: bool = True
) -> dict:
    """
    Plan RDS database capacity.

    Args:
        connections: Max concurrent connections
        storage_gb: Storage needed in GB
        iops_required: IOPS requirement
        multi_az: Whether to use Multi-AZ
    """
    # Connection to instance size mapping (PostgreSQL)
    # db.t3.micro supports ~50 connections
    # db.m5.large supports ~1000 connections
    if connections < 100:
        instance_class = 'db.t3.small'
        vcpu = 2
        memory_gb = 2
        base_cost_hour = 0.034
    elif connections < 500:
        instance_class = 'db.m5.large'
        vcpu = 2
        memory_gb = 8
        base_cost_hour = 0.192
    elif connections < 1500:
        instance_class = 'db.m5.xlarge'
        vcpu = 4
        memory_gb = 16
        base_cost_hour = 0.384
    else:
        instance_class = 'db.m5.2xlarge'
        vcpu = 8
        memory_gb = 32
        base_cost_hour = 0.768

    # Storage cost
    if iops_required > 16000:
        storage_type = 'io2'
        storage_cost_gb_month = 0.125
        iops_cost_month = iops_required * 0.065
    elif iops_required > 3000:
        storage_type = 'io1'
        storage_cost_gb_month = 0.125
        iops_cost_month = iops_required * 0.10
    else:
        storage_type = 'gp3'
        storage_cost_gb_month = 0.115
        iops_cost_month = 0  # 3000 IOPS included

    storage_cost_month = storage_gb * storage_cost_gb_month + iops_cost_month

    # Instance cost
    instance_cost_month = base_cost_hour * 730
    if multi_az:
        instance_cost_month *= 2

    total_monthly_cost = instance_cost_month + storage_cost_month

    return {
        'instance_class': instance_class,
        'vcpu': vcpu,
        'memory_gb': memory_gb,
        'storage_type': storage_type,
        'storage_gb': storage_gb,
        'provisioned_iops': iops_required if iops_required > 3000 else 3000,
        'multi_az': multi_az,
        'instance_cost_monthly': instance_cost_month,
        'storage_cost_monthly': storage_cost_month,
        'total_monthly_cost': total_monthly_cost,
        'max_connections': connections
    }
```

### 7.2 GCP Capacity Planning

**GCE Instance Selection**:
```python
def select_gce_instance(
    cpu_required: float,
    memory_required_gb: float,
    region: str = 'us-central1'
) -> dict:
    """
    Recommend GCE machine type.

    Args:
        cpu_required: vCPUs needed
        memory_required_gb: Memory in GB
        region: GCP region
    """
    # GCE machine types
    machine_types = [
        {'type': 'e2-small', 'vcpu': 2, 'memory_gb': 2, 'cost_hour': 0.033},
        {'type': 'e2-medium', 'vcpu': 2, 'memory_gb': 4, 'cost_hour': 0.067},
        {'type': 'n1-standard-1', 'vcpu': 1, 'memory_gb': 3.75, 'cost_hour': 0.0475},
        {'type': 'n1-standard-2', 'vcpu': 2, 'memory_gb': 7.5, 'cost_hour': 0.095},
        {'type': 'n1-standard-4', 'vcpu': 4, 'memory_gb': 15, 'cost_hour': 0.19},
        {'type': 'n2-standard-2', 'vcpu': 2, 'memory_gb': 8, 'cost_hour': 0.097},
        {'type': 'n2-standard-4', 'vcpu': 4, 'memory_gb': 16, 'cost_hour': 0.194},
        {'type': 'n2-highmem-2', 'vcpu': 2, 'memory_gb': 16, 'cost_hour': 0.130},
        {'type': 'n2-highcpu-4', 'vcpu': 4, 'memory_gb': 4, 'cost_hour': 0.142},
    ]

    # Filter and sort
    suitable = [
        m for m in machine_types
        if m['vcpu'] >= cpu_required and m['memory_gb'] >= memory_required_gb
    ]

    if not suitable:
        return {'error': 'No suitable machine type found'}

    suitable.sort(key=lambda x: x['cost_hour'])
    recommended = suitable[0]

    return {
        'machine_type': recommended['type'],
        'vcpu': recommended['vcpu'],
        'memory_gb': recommended['memory_gb'],
        'hourly_cost': recommended['cost_hour'],
        'monthly_cost': recommended['cost_hour'] * 730,
        'region': region
    }
```

### 7.3 Azure Capacity Planning

**Azure VM Selection**:
```python
def select_azure_vm(
    cpu_required: float,
    memory_required_gb: float,
    region: str = 'eastus'
) -> dict:
    """
    Recommend Azure VM size.

    Args:
        cpu_required: vCPUs needed
        memory_required_gb: Memory in GB
        region: Azure region
    """
    # Azure VM sizes
    vm_sizes = [
        {'size': 'B2s', 'vcpu': 2, 'memory_gb': 4, 'cost_hour': 0.042},
        {'size': 'B2ms', 'vcpu': 2, 'memory_gb': 8, 'cost_hour': 0.083},
        {'size': 'D2s_v3', 'vcpu': 2, 'memory_gb': 8, 'cost_hour': 0.096},
        {'size': 'D4s_v3', 'vcpu': 4, 'memory_gb': 16, 'cost_hour': 0.192},
        {'size': 'D8s_v3', 'vcpu': 8, 'memory_gb': 32, 'cost_hour': 0.384},
        {'size': 'E2s_v3', 'vcpu': 2, 'memory_gb': 16, 'cost_hour': 0.126},
        {'size': 'F4s_v2', 'vcpu': 4, 'memory_gb': 8, 'cost_hour': 0.17},
    ]

    suitable = [
        vm for vm in vm_sizes
        if vm['vcpu'] >= cpu_required and vm['memory_gb'] >= memory_required_gb
    ]

    if not suitable:
        return {'error': 'No suitable VM size found'}

    suitable.sort(key=lambda x: x['cost_hour'])
    recommended = suitable[0]

    return {
        'vm_size': recommended['size'],
        'vcpu': recommended['vcpu'],
        'memory_gb': recommended['memory_gb'],
        'hourly_cost': recommended['cost_hour'],
        'monthly_cost': recommended['cost_hour'] * 730,
        'region': region
    }
```

---

## 8. Database Capacity Planning

### 8.1 Connection Pool Sizing

**Connection Pool Calculation**:
```python
def calculate_connection_pool_size(
    concurrent_requests: int,
    avg_query_duration_ms: float,
    request_duration_ms: float,
    safety_factor: float = 1.3
) -> dict:
    """
    Calculate optimal database connection pool size.

    Args:
        concurrent_requests: Number of concurrent requests
        avg_query_duration_ms: Average query execution time
        request_duration_ms: Average request duration
        safety_factor: Multiplier for safety margin

    Formula:
        pool_size = concurrent_requests × (query_time / request_time) × safety_factor
    """
    # Calculate pool size
    queries_per_request = avg_query_duration_ms / request_duration_ms
    base_pool_size = concurrent_requests * queries_per_request
    recommended_pool_size = int(np.ceil(base_pool_size * safety_factor))

    # Industry rule of thumb: pool_size = ((core_count × 2) + effective_spindle_count)
    # For cloud databases, use:
    rule_of_thumb_size = 10  # Minimum recommended

    final_size = max(recommended_pool_size, rule_of_thumb_size)

    return {
        'calculated_pool_size': recommended_pool_size,
        'recommended_pool_size': final_size,
        'min_pool_size': max(5, int(final_size * 0.5)),
        'max_pool_size': final_size,
        'queries_per_request': queries_per_request,
        'safety_factor': safety_factor
    }

# Example
pool_config = calculate_connection_pool_size(
    concurrent_requests=200,
    avg_query_duration_ms=50,
    request_duration_ms=200,
    safety_factor=1.3
)
```

### 8.2 Database Sizing

**PostgreSQL Sizing**:
```python
def size_postgresql_database(
    rows_per_table: dict,
    avg_row_size_bytes: dict,
    index_overhead: float = 0.30,
    wal_retention_gb: float = 10,
    temp_space_gb: float = 5
) -> dict:
    """
    Calculate PostgreSQL storage requirements.

    Args:
        rows_per_table: {'users': 1000000, 'orders': 5000000}
        avg_row_size_bytes: {'users': 200, 'orders': 150}
        index_overhead: Percentage for indexes (30% typical)
        wal_retention_gb: WAL log retention
        temp_space_gb: Temporary table space
    """
    total_data_gb = 0
    table_sizes = {}

    for table, rows in rows_per_table.items():
        row_size = avg_row_size_bytes.get(table, 100)
        table_size_bytes = rows * row_size
        table_size_gb = table_size_bytes / (1024 ** 3)

        table_sizes[table] = table_size_gb
        total_data_gb += table_size_gb

    # Add index overhead
    index_size_gb = total_data_gb * index_overhead

    # Total storage
    total_storage_gb = (
        total_data_gb +
        index_size_gb +
        wal_retention_gb +
        temp_space_gb
    )

    # Add 30% growth buffer
    total_with_buffer = total_storage_gb * 1.3

    return {
        'data_size_gb': total_data_gb,
        'index_size_gb': index_size_gb,
        'wal_size_gb': wal_retention_gb,
        'temp_size_gb': temp_space_gb,
        'total_storage_gb': total_storage_gb,
        'total_with_buffer_gb': total_with_buffer,
        'table_breakdown': table_sizes
    }
```

**MongoDB Sizing**:
```python
def size_mongodb_database(
    collections: dict,
    avg_document_size_bytes: dict,
    index_count_per_collection: dict,
    avg_index_size_bytes: int = 50,
    replication_factor: int = 3,
    oplog_hours: int = 24
) -> dict:
    """
    Calculate MongoDB storage requirements.

    Args:
        collections: {'users': 1000000, 'orders': 5000000}
        avg_document_size_bytes: {'users': 500, 'orders': 300}
        index_count_per_collection: {'users': 5, 'orders': 8}
        avg_index_size_bytes: Average bytes per index entry
        replication_factor: Number of replicas
        oplog_hours: Oplog retention in hours
    """
    total_data_gb = 0
    total_index_gb = 0

    for collection, count in collections.items():
        doc_size = avg_document_size_bytes.get(collection, 200)
        data_bytes = count * doc_size
        data_gb = data_bytes / (1024 ** 3)
        total_data_gb += data_gb

        # Indexes
        index_count = index_count_per_collection.get(collection, 3)
        index_bytes = count * index_count * avg_index_size_bytes
        index_gb = index_bytes / (1024 ** 3)
        total_index_gb += index_gb

    # Oplog sizing (typically 5% of data size per hour)
    oplog_rate_gb_hour = total_data_gb * 0.05
    oplog_gb = oplog_rate_gb_hour * oplog_hours

    # Total per node
    total_per_node_gb = total_data_gb + total_index_gb + oplog_gb

    # Total cluster
    total_cluster_gb = total_per_node_gb * replication_factor

    return {
        'data_size_gb': total_data_gb,
        'index_size_gb': total_index_gb,
        'oplog_size_gb': oplog_gb,
        'total_per_node_gb': total_per_node_gb,
        'replication_factor': replication_factor,
        'total_cluster_gb': total_cluster_gb,
        'recommended_storage_per_node_gb': total_per_node_gb * 1.5  # 50% buffer
    }
```

### 8.3 Query Performance and IOPS

**IOPS Requirements**:
```python
def calculate_database_iops(
    queries_per_second: float,
    reads_per_query: float = 2,
    writes_per_query: float = 0.5,
    index_reads_per_query: float = 3
) -> dict:
    """
    Calculate database IOPS requirements.

    Args:
        queries_per_second: Query rate
        reads_per_query: Data block reads per query
        writes_per_query: Data block writes per query
        index_reads_per_query: Index block reads per query
    """
    # Read IOPS
    data_reads_per_sec = queries_per_second * reads_per_query
    index_reads_per_sec = queries_per_second * index_reads_per_query
    total_read_iops = data_reads_per_sec + index_reads_per_sec

    # Write IOPS (includes WAL writes)
    data_writes_per_sec = queries_per_second * writes_per_query
    wal_writes_per_sec = data_writes_per_sec * 2  # WAL + data
    total_write_iops = wal_writes_per_sec

    # Total
    total_iops = total_read_iops + total_write_iops

    # Recommend storage type
    if total_iops < 3000:
        storage_type = 'gp3 (General Purpose SSD)'
        provisioned_iops = 3000
    elif total_iops < 16000:
        storage_type = 'io1/io2 (Provisioned IOPS SSD)'
        provisioned_iops = int(np.ceil(total_iops / 100) * 100)
    else:
        storage_type = 'io2 Block Express'
        provisioned_iops = int(np.ceil(total_iops / 1000) * 1000)

    return {
        'queries_per_second': queries_per_second,
        'read_iops': total_read_iops,
        'write_iops': total_write_iops,
        'total_iops': total_iops,
        'recommended_storage_type': storage_type,
        'recommended_provisioned_iops': provisioned_iops
    }
```

---

## 9. Network Capacity Planning

### 9.1 Content Delivery Network (CDN)

**CDN Bandwidth Calculation**:
```python
def calculate_cdn_requirements(
    page_views_per_day: int,
    avg_page_size_kb: float,
    cache_hit_rate: float = 0.85,
    peak_to_avg_ratio: float = 3.0
) -> dict:
    """
    Calculate CDN bandwidth and cost.

    Args:
        page_views_per_day: Daily page views
        avg_page_size_kb: Average page size in KB
        cache_hit_rate: CDN cache hit rate (0.0-1.0)
        peak_to_avg_ratio: Peak traffic vs average
    """
    # Calculate traffic
    total_traffic_gb_day = (page_views_per_day * avg_page_size_kb) / (1024 * 1024)

    # CDN serves most traffic
    cdn_traffic_gb_day = total_traffic_gb_day * cache_hit_rate
    origin_traffic_gb_day = total_traffic_gb_day * (1 - cache_hit_rate)

    # Monthly traffic
    cdn_traffic_gb_month = cdn_traffic_gb_day * 30
    origin_traffic_gb_month = origin_traffic_gb_day * 30

    # Bandwidth (peak)
    avg_bandwidth_mbps = (total_traffic_gb_day * 1024 * 8) / (24 * 3600)
    peak_bandwidth_mbps = avg_bandwidth_mbps * peak_to_avg_ratio

    # Cost estimation (CloudFront pricing example)
    cdn_cost_per_gb = 0.085  # First 10 TB
    origin_bandwidth_cost = origin_traffic_gb_month * 0.09  # Data transfer out
    cdn_bandwidth_cost = cdn_traffic_gb_month * cdn_cost_per_gb

    total_monthly_cost = cdn_bandwidth_cost + origin_bandwidth_cost

    return {
        'page_views_per_day': page_views_per_day,
        'total_traffic_gb_month': total_traffic_gb_day * 30,
        'cdn_traffic_gb_month': cdn_traffic_gb_month,
        'origin_traffic_gb_month': origin_traffic_gb_month,
        'cache_hit_rate_percent': cache_hit_rate * 100,
        'avg_bandwidth_mbps': avg_bandwidth_mbps,
        'peak_bandwidth_mbps': peak_bandwidth_mbps,
        'estimated_monthly_cost': total_monthly_cost,
        'cdn_cost': cdn_bandwidth_cost,
        'origin_cost': origin_bandwidth_cost
    }
```

### 9.2 Load Balancer Capacity

**Load Balancer Sizing**:
```python
def calculate_load_balancer_capacity(
    requests_per_second: int,
    avg_request_size_kb: float,
    avg_response_size_kb: float,
    connections_per_request: float = 1.2,  # Keep-alive reduces this
    ssl_enabled: bool = True
) -> dict:
    """
    Calculate load balancer capacity requirements.

    Args:
        requests_per_second: Request rate
        avg_request_size_kb: Average request size
        avg_response_size_kb: Average response size
        connections_per_request: Connection overhead
        ssl_enabled: Whether SSL/TLS termination is used
    """
    # Bandwidth
    ingress_mbps = (requests_per_second * avg_request_size_kb * 8) / 1024
    egress_mbps = (requests_per_second * avg_response_size_kb * 8) / 1024

    # Connections
    new_connections_per_sec = requests_per_second * connections_per_request
    avg_connection_duration_sec = 5  # Typical keep-alive
    concurrent_connections = new_connections_per_sec * avg_connection_duration_sec

    # SSL overhead (adds ~10% CPU overhead)
    if ssl_enabled:
        ssl_overhead_factor = 1.10
        ssl_handshakes_per_sec = new_connections_per_sec * 0.1  # 10% are new
    else:
        ssl_overhead_factor = 1.0
        ssl_handshakes_per_sec = 0

    # Recommend LB type
    if requests_per_second < 1000:
        lb_type = 'Application Load Balancer (ALB) - 1 instance'
        capacity_units = 1
    elif requests_per_second < 10000:
        lb_type = 'Application Load Balancer (ALB) - Standard'
        capacity_units = int(np.ceil(requests_per_second / 1000))
    else:
        lb_type = 'Application Load Balancer (ALB) - High traffic'
        capacity_units = int(np.ceil(requests_per_second / 1000))

    return {
        'requests_per_second': requests_per_second,
        'ingress_mbps': ingress_mbps,
        'egress_mbps': egress_mbps,
        'concurrent_connections': int(concurrent_connections),
        'new_connections_per_sec': int(new_connections_per_sec),
        'ssl_enabled': ssl_enabled,
        'ssl_handshakes_per_sec': int(ssl_handshakes_per_sec),
        'recommended_lb_type': lb_type,
        'capacity_units': capacity_units
    }
```

---

## 10. Traffic Analysis and Prediction

### 10.1 Seasonal Patterns

**Detect Seasonality**:
```python
from statsmodels.tsa.seasonal import seasonal_decompose

def detect_seasonality(data: np.ndarray, period: int = 7) -> dict:
    """
    Detect and extract seasonal patterns.

    Args:
        data: Time series data
        period: Seasonal period (7 for weekly, 365 for yearly)
    """
    # Decompose time series
    result = seasonal_decompose(
        data,
        model='additive',  # or 'multiplicative'
        period=period,
        extrapolate_trend='freq'
    )

    # Seasonal strength
    seasonal_var = np.var(result.seasonal)
    residual_var = np.var(result.resid[~np.isnan(result.resid)])
    seasonal_strength = 1 - (residual_var / (seasonal_var + residual_var))

    return {
        'trend': result.trend,
        'seasonal': result.seasonal,
        'residual': result.resid,
        'seasonal_strength': seasonal_strength,
        'has_strong_seasonality': seasonal_strength > 0.6
    }
```

### 10.2 Growth Rate Analysis

**Calculate Growth Rates**:
```python
def analyze_growth_rate(data: np.ndarray, periods: int = 30) -> dict:
    """
    Analyze growth rates over time.

    Args:
        data: Time series data
        periods: Period for growth calculation
    """
    # Simple growth rate
    simple_growth = ((data[-1] - data[0]) / data[0]) * 100

    # Compound annual growth rate (CAGR)
    n_years = len(data) / 365
    if n_years > 0:
        cagr = ((data[-1] / data[0]) ** (1 / n_years) - 1) * 100
    else:
        cagr = 0

    # Month-over-month growth
    monthly_growth_rates = []
    for i in range(30, len(data), 30):
        month_start = data[i-30]
        month_end = data[i]
        if month_start > 0:
            growth = ((month_end - month_start) / month_start) * 100
            monthly_growth_rates.append(growth)

    avg_monthly_growth = np.mean(monthly_growth_rates) if monthly_growth_rates else 0

    return {
        'simple_growth_percent': simple_growth,
        'cagr_percent': cagr,
        'avg_monthly_growth_percent': avg_monthly_growth,
        'monthly_growth_rates': monthly_growth_rates,
        'is_accelerating': len(monthly_growth_rates) > 2 and monthly_growth_rates[-1] > monthly_growth_rates[-2]
    }
```

### 10.3 Anomaly Detection

**Detect Traffic Anomalies**:
```python
from sklearn.ensemble import IsolationForest

def detect_traffic_anomalies(
    data: np.ndarray,
    contamination: float = 0.05
) -> dict:
    """
    Detect anomalies in traffic data.

    Args:
        data: Time series data
        contamination: Expected proportion of anomalies
    """
    # Reshape for sklearn
    X = data.reshape(-1, 1)

    # Fit Isolation Forest
    clf = IsolationForest(contamination=contamination, random_state=42)
    predictions = clf.fit_predict(X)

    # Anomalies are labeled -1
    anomaly_indices = np.where(predictions == -1)[0]
    anomaly_values = data[anomaly_indices]

    # Statistical anomaly detection (Z-score)
    z_scores = np.abs((data - np.mean(data)) / np.std(data))
    statistical_anomalies = np.where(z_scores > 3)[0]

    return {
        'anomaly_count': len(anomaly_indices),
        'anomaly_indices': anomaly_indices.tolist(),
        'anomaly_values': anomaly_values.tolist(),
        'anomaly_percent': (len(anomaly_indices) / len(data)) * 100,
        'statistical_anomalies': statistical_anomalies.tolist(),
        'max_z_score': np.max(z_scores)
    }
```

---

## 11. Disaster Recovery Capacity

### 11.1 RTO/RPO Requirements

**Calculate DR Capacity**:
```python
def calculate_dr_capacity(
    rto_hours: float,
    rpo_minutes: float,
    production_capacity: dict,
    dr_strategy: str = 'hot'
) -> dict:
    """
    Calculate disaster recovery capacity requirements.

    Args:
        rto_hours: Recovery Time Objective in hours
        rpo_minutes: Recovery Point Objective in minutes
        production_capacity: Production capacity specs
        dr_strategy: 'hot', 'warm', or 'cold'
    """
    # DR capacity as percentage of production
    dr_capacity_ratio = {
        'hot': 1.0,    # 100% capacity, active-active
        'warm': 0.5,   # 50% capacity, active-passive
        'cold': 0.1    # 10% capacity, backup only
    }

    capacity_ratio = dr_capacity_ratio.get(dr_strategy, 0.5)

    # Calculate DR resources
    dr_instances = int(np.ceil(production_capacity['instances'] * capacity_ratio))
    dr_storage = production_capacity['storage_gb'] * 1.2  # 20% extra for backups

    # Replication bandwidth
    if rpo_minutes < 5:
        replication_type = 'Synchronous'
        bandwidth_multiplier = 1.5  # Real-time replication
    elif rpo_minutes < 60:
        replication_type = 'Near-synchronous'
        bandwidth_multiplier = 0.5
    else:
        replication_type = 'Asynchronous'
        bandwidth_multiplier = 0.1

    replication_bandwidth_mbps = (
        production_capacity.get('bandwidth_mbps', 100) * bandwidth_multiplier
    )

    # Cost estimation
    monthly_cost = (
        dr_instances * production_capacity.get('cost_per_instance', 100) +
        dr_storage * 0.023 +  # Storage cost
        replication_bandwidth_mbps * 10  # Bandwidth cost
    )

    return {
        'dr_strategy': dr_strategy,
        'rto_hours': rto_hours,
        'rpo_minutes': rpo_minutes,
        'capacity_ratio': capacity_ratio,
        'dr_instances': dr_instances,
        'dr_storage_gb': dr_storage,
        'replication_type': replication_type,
        'replication_bandwidth_mbps': replication_bandwidth_mbps,
        'estimated_monthly_cost': monthly_cost,
        'production_cost_ratio': capacity_ratio
    }
```

### 11.2 Backup Capacity

**Backup Storage Calculation**:
```python
def calculate_backup_storage(
    data_size_gb: float,
    daily_change_rate: float = 0.05,
    retention_days: int = 30,
    backup_frequency_hours: int = 24,
    compression_ratio: float = 0.5
) -> dict:
    """
    Calculate backup storage requirements.

    Args:
        data_size_gb: Total data size
        daily_change_rate: Percentage of data that changes daily
        retention_days: How long to keep backups
        backup_frequency_hours: Hours between backups
        compression_ratio: Compression efficiency (0.5 = 50% size)
    """
    # Full backup
    full_backup_size = data_size_gb * compression_ratio

    # Incremental backups
    daily_change_gb = data_size_gb * daily_change_rate
    incremental_backup_size = daily_change_gb * compression_ratio

    # Total backups per retention period
    backups_per_day = 24 / backup_frequency_hours
    total_backups = int(retention_days * backups_per_day)

    # Storage calculation
    # 1 full backup + incremental backups
    total_backup_storage = full_backup_size + (incremental_backup_size * (total_backups - 1))

    # Add 20% safety margin
    total_with_margin = total_backup_storage * 1.2

    return {
        'data_size_gb': data_size_gb,
        'full_backup_size_gb': full_backup_size,
        'incremental_backup_size_gb': incremental_backup_size,
        'total_backups': total_backups,
        'total_backup_storage_gb': total_backup_storage,
        'total_with_margin_gb': total_with_margin,
        'retention_days': retention_days,
        'backup_frequency_hours': backup_frequency_hours
    }
```

---

## 12. Compliance and Headroom

### 12.1 N+1 and N+2 Redundancy

**Redundancy Calculation**:
```python
def calculate_redundancy_requirements(
    baseline_capacity: int,
    redundancy_type: str = 'n_plus_1',
    availability_target: float = 0.9999
) -> dict:
    """
    Calculate redundancy requirements for high availability.

    Args:
        baseline_capacity: Minimum instances needed for load
        redundancy_type: 'n_plus_1', 'n_plus_2', 'n_plus_n'
        availability_target: Target availability (0.9999 = 99.99%)
    """
    if redundancy_type == 'n_plus_1':
        total_instances = baseline_capacity + 1
        failure_tolerance = 1
        description = 'Can survive 1 instance failure'
    elif redundancy_type == 'n_plus_2':
        total_instances = baseline_capacity + 2
        failure_tolerance = 2
        description = 'Can survive 2 instance failures'
    elif redundancy_type == 'n_plus_n':
        total_instances = baseline_capacity * 2
        failure_tolerance = baseline_capacity
        description = 'Can survive losing entire cluster'
    else:
        total_instances = baseline_capacity
        failure_tolerance = 0
        description = 'No redundancy'

    # Calculate availability
    # Assuming instance availability = 0.99 (99%)
    instance_availability = 0.99

    # System availability with N+1: 1 - (1 - p)^(n+1)
    system_availability = 1 - (1 - instance_availability) ** total_instances

    meets_target = system_availability >= availability_target

    return {
        'baseline_capacity': baseline_capacity,
        'redundancy_type': redundancy_type,
        'total_instances': total_instances,
        'failure_tolerance': failure_tolerance,
        'system_availability': system_availability,
        'availability_target': availability_target,
        'meets_target': meets_target,
        'description': description,
        'overhead_percent': ((total_instances - baseline_capacity) / baseline_capacity) * 100
    }
```

### 12.2 Capacity Headroom

**Headroom Monitoring**:
```python
def monitor_capacity_headroom(
    current_usage: float,
    total_capacity: float,
    target_utilization: float = 0.70,
    forecast_growth_rate: float = 0.05
) -> dict:
    """
    Monitor capacity headroom and project time to capacity.

    Args:
        current_usage: Current resource usage
        total_capacity: Total available capacity
        target_utilization: Target utilization threshold
        forecast_growth_rate: Monthly growth rate
    """
    current_utilization = current_usage / total_capacity
    target_capacity = total_capacity * target_utilization
    remaining_headroom = target_capacity - current_usage
    remaining_headroom_percent = (remaining_headroom / total_capacity) * 100

    # Time to capacity exhaustion
    if forecast_growth_rate > 0 and remaining_headroom > 0:
        # Months until target capacity reached
        months_to_capacity = np.log(target_capacity / current_usage) / np.log(1 + forecast_growth_rate)

        # Months until full capacity
        months_to_full = np.log(total_capacity / current_usage) / np.log(1 + forecast_growth_rate)
    else:
        months_to_capacity = float('inf')
        months_to_full = float('inf')

    # Alert levels
    if current_utilization >= target_utilization:
        alert_level = 'CRITICAL'
        message = 'At or above target capacity'
    elif months_to_capacity < 1:
        alert_level = 'WARNING'
        message = f'Will reach capacity in {months_to_capacity:.1f} months'
    elif months_to_capacity < 3:
        alert_level = 'CAUTION'
        message = f'Will reach capacity in {months_to_capacity:.1f} months'
    else:
        alert_level = 'OK'
        message = 'Sufficient headroom'

    return {
        'current_usage': current_usage,
        'total_capacity': total_capacity,
        'current_utilization_percent': current_utilization * 100,
        'target_utilization_percent': target_utilization * 100,
        'remaining_headroom': remaining_headroom,
        'remaining_headroom_percent': remaining_headroom_percent,
        'months_to_target_capacity': months_to_capacity,
        'months_to_full_capacity': months_to_full,
        'alert_level': alert_level,
        'message': message
    }
```

---

## 13. Capacity Planning Tools

### 13.1 Open Source Tools

**Prometheus + Grafana**:
- Metrics collection and visualization
- Alerting on capacity thresholds
- Historical data for trend analysis

**Netdata**:
- Real-time performance monitoring
- Automatic anomaly detection
- Low overhead

**VictoriaMetrics**:
- Long-term metrics storage
- Efficient compression
- PromQL compatible

**Telegraf + InfluxDB**:
- Metrics collection agent
- Time-series database
- Downsampling and retention policies

### 13.2 Cloud Provider Tools

**AWS**:
- CloudWatch metrics and alarms
- AWS Compute Optimizer
- AWS Trusted Advisor
- Cost Explorer

**GCP**:
- Cloud Monitoring
- Cloud Logging
- Recommender API
- Active Assist

**Azure**:
- Azure Monitor
- Azure Advisor
- Cost Management + Billing

### 13.3 Commercial Tools

**Datadog**:
- Infrastructure monitoring
- APM with capacity insights
- Anomaly detection
- Forecasting

**New Relic**:
- Full-stack observability
- Capacity planning dashboards
- Alerting and anomaly detection

**Dynatrace**:
- AI-powered monitoring
- Automatic baselining
- Predictive alerting

---

## 14. Production Best Practices

### 14.1 Capacity Planning Checklist

**Monthly Review**:
- [ ] Review utilization trends across all resources
- [ ] Update forecasts based on actual growth
- [ ] Identify over-provisioned resources
- [ ] Plan capacity for upcoming launches
- [ ] Review and optimize auto-scaling policies
- [ ] Analyze cost trends and optimization opportunities

**Quarterly Planning**:
- [ ] Conduct load testing
- [ ] Update capacity models
- [ ] Review disaster recovery capacity
- [ ] Evaluate new instance types and services
- [ ] Update documentation and runbooks
- [ ] Train team on capacity procedures

**Annual Strategy**:
- [ ] Long-term capacity roadmap
- [ ] Architecture review for scalability
- [ ] Reserved capacity planning
- [ ] Budget planning
- [ ] Disaster recovery testing

### 14.2 Documentation Standards

**Capacity Plan Document**:
```markdown
# Capacity Plan - [Service Name]

## Current State
- Current capacity: X instances, Y GB storage
- Current utilization: A% CPU, B% memory
- Current cost: $Z/month

## Forecast
- Expected growth: X% per month
- Peak traffic projection: Y req/s
- Forecast horizon: N months

## Capacity Changes
- Add X instances by [date]
- Increase storage by Y GB by [date]
- Implement auto-scaling by [date]

## Cost Impact
- Current: $A/month
- Projected: $B/month
- Delta: $C/month (+D%)

## Risks and Mitigations
- Risk: ...
  Mitigation: ...

## Approval
- Reviewed by: ...
- Approved by: ...
- Date: ...
```

### 14.3 Monitoring and Alerting

**Key Metrics to Monitor**:
- CPU utilization (per instance and aggregate)
- Memory utilization
- Disk space usage and IOPS
- Network bandwidth
- Request rate and latency
- Error rates
- Queue depths
- Database connections

**Alert Thresholds**:
```yaml
alerts:
  cpu_high:
    threshold: 80%
    duration: 10m
    severity: warning

  cpu_critical:
    threshold: 90%
    duration: 5m
    severity: critical

  disk_space_low:
    threshold: 80%
    duration: 5m
    severity: warning

  headroom_low:
    threshold: 90% of target capacity
    duration: 1h
    severity: warning
```

---

## Conclusion

Effective capacity planning requires:

1. **Data-Driven Decisions**: Collect and analyze metrics
2. **Accurate Forecasting**: Use appropriate methods for your patterns
3. **Headroom Planning**: Never run at 100% capacity
4. **Regular Testing**: Load test before issues arise
5. **Cost Optimization**: Right-size and use appropriate pricing models
6. **Automation**: Auto-scale when possible
7. **Documentation**: Keep capacity plans updated
8. **Continuous Review**: Monitor, measure, adjust

Remember: It's better to have capacity and not need it than to need capacity and not have it. The cost of downtime often exceeds the cost of over-provisioning by orders of magnitude.

---

**Document Version**: 1.0
**Last Updated**: 2025-10-29
**Next Review**: 2025-11-29
