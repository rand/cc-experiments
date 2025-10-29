#!/usr/bin/env python3
"""
Complete Prophet-based Capacity Forecasting Example

This example demonstrates:
- Loading historical capacity data
- Training Prophet model with seasonality
- Generating 90-day forecast
- Visualizing results
- Exporting forecasts

Usage:
    python prophet_forecast.py --input ../../../test-data/cpu_usage.csv
    python prophet_forecast.py --prometheus http://localhost:9090 --query 'cpu_usage'
"""

import argparse
import pandas as pd
import numpy as np
from prophet import Prophet
import matplotlib.pyplot as plt
from datetime import datetime, timedelta


def load_data(input_file):
    """Load historical capacity data."""
    df = pd.read_csv(input_file)

    # Prophet requires columns named 'ds' (date) and 'y' (value)
    if 'ds' not in df.columns:
        df['ds'] = pd.to_datetime(df.iloc[:, 0])
    if 'y' not in df.columns:
        df['y'] = pd.to_numeric(df.iloc[:, 1])

    df = df[['ds', 'y']].dropna()

    print(f"Loaded {len(df)} data points")
    print(f"Date range: {df['ds'].min()} to {df['ds'].max()}")
    print(f"Value range: {df['y'].min():.2f} to {df['y'].max():.2f}")

    return df


def train_prophet_model(df, seasonality='auto'):
    """Train Prophet forecasting model."""
    print("\nTraining Prophet model...")

    model = Prophet(
        yearly_seasonality=seasonality in ['auto', 'yearly'],
        weekly_seasonality=seasonality in ['auto', 'weekly'],
        daily_seasonality=seasonality == 'daily',
        interval_width=0.95,
        changepoint_prior_scale=0.05  # Flexibility of trend changes
    )

    # Add custom seasonality if needed
    if seasonality == 'monthly':
        model.add_seasonality(
            name='monthly',
            period=30.5,
            fourier_order=5
        )

    model.fit(df)

    print("Model trained successfully")
    return model


def generate_forecast(model, df, forecast_days=90):
    """Generate capacity forecast."""
    print(f"\nGenerating {forecast_days}-day forecast...")

    # Create future dataframe
    future = model.make_future_dataframe(periods=forecast_days, freq='D')

    # Generate forecast
    forecast = model.predict(future)

    # Extract forecast period
    forecast_period = forecast.tail(forecast_days)

    print(f"Forecast range: {forecast_period['yhat'].min():.2f} to {forecast_period['yhat'].max():.2f}")
    print(f"Confidence interval: [{forecast_period['yhat_lower'].min():.2f}, {forecast_period['yhat_upper'].max():.2f}]")

    return forecast


def visualize_forecast(model, df, forecast, output_file='forecast.png'):
    """Visualize forecast with components."""
    print(f"\nGenerating visualizations...")

    fig = plt.figure(figsize=(16, 12))

    # Main forecast plot
    ax1 = plt.subplot(3, 1, 1)
    model.plot(forecast, ax=ax1)
    ax1.set_title('Capacity Forecast with Confidence Interval', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Capacity Utilization (%)')
    ax1.grid(True, alpha=0.3)

    # Add capacity thresholds
    ax1.axhline(y=70, color='green', linestyle='--', alpha=0.5, label='Target (70%)')
    ax1.axhline(y=85, color='red', linestyle='--', alpha=0.5, label='Critical (85%)')
    ax1.legend()

    # Components plot
    ax2 = plt.subplot(3, 1, 2)
    if 'trend' in forecast.columns:
        ax2.plot(forecast['ds'], forecast['trend'], label='Trend', linewidth=2)
    ax2.set_title('Trend Component', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Trend')
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    # Seasonality plot
    ax3 = plt.subplot(3, 1, 3)
    if 'weekly' in forecast.columns:
        ax3.plot(forecast['ds'], forecast['weekly'], label='Weekly Seasonality', linewidth=2)
    elif 'yearly' in forecast.columns:
        ax3.plot(forecast['ds'], forecast['yearly'], label='Yearly Seasonality', linewidth=2)
    ax3.set_title('Seasonality Component', fontsize=12, fontweight='bold')
    ax3.set_xlabel('Date')
    ax3.set_ylabel('Seasonal Effect')
    ax3.grid(True, alpha=0.3)
    ax3.legend()

    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    print(f"Visualization saved to {output_file}")


def export_forecast(forecast, forecast_days, output_file='forecast_results.csv'):
    """Export forecast results to CSV."""
    print(f"\nExporting forecast to {output_file}...")

    # Extract forecast period
    forecast_period = forecast.tail(forecast_days)

    # Create export dataframe
    export_df = pd.DataFrame({
        'date': forecast_period['ds'],
        'forecast': forecast_period['yhat'],
        'lower_bound': forecast_period['yhat_lower'],
        'upper_bound': forecast_period['yhat_upper']
    })

    export_df.to_csv(output_file, index=False)
    print(f"Exported {len(export_df)} forecast points")


def capacity_analysis(df, forecast, forecast_days):
    """Analyze capacity requirements."""
    print("\n=== Capacity Analysis ===")

    # Current state
    current_avg = df['y'].tail(30).mean()
    current_max = df['y'].tail(30).max()

    print(f"\nCurrent State (Last 30 days):")
    print(f"  Average utilization: {current_avg:.2f}%")
    print(f"  Maximum utilization: {current_max:.2f}%")

    # Forecast analysis
    forecast_period = forecast.tail(forecast_days)
    forecast_avg = forecast_period['yhat'].mean()
    forecast_max = forecast_period['yhat_upper'].quantile(0.95)

    print(f"\nForecast ({forecast_days} days):")
    print(f"  Average utilization: {forecast_avg:.2f}%")
    print(f"  P95 utilization (upper bound): {forecast_max:.2f}%")

    # Capacity recommendations
    print(f"\nRecommendations:")

    if forecast_max > 85:
        print("  ⚠️  CRITICAL: Forecast exceeds 85% utilization")
        print("  Action: Add capacity immediately")
        required_capacity_increase = ((forecast_max - 70) / 70) * 100
        print(f"  Recommended capacity increase: {required_capacity_increase:.1f}%")
    elif forecast_max > 70:
        print("  ⚠️  WARNING: Forecast approaching 70% target")
        print("  Action: Plan capacity addition within 30 days")
    else:
        print("  ✓ OK: Sufficient capacity for forecast period")

    # Growth rate
    growth_rate = ((forecast_avg - current_avg) / current_avg) * 100 / (forecast_days / 30)
    print(f"\n  Monthly growth rate: {growth_rate:.2f}%")


def main():
    parser = argparse.ArgumentParser(description='Prophet-based capacity forecasting')
    parser.add_argument('--input', required=True, help='Input CSV file')
    parser.add_argument('--forecast-days', type=int, default=90, help='Days to forecast')
    parser.add_argument('--seasonality', choices=['auto', 'yearly', 'weekly', 'monthly', 'daily'],
                        default='auto', help='Seasonality pattern')
    parser.add_argument('--visualize', action='store_true', help='Generate visualization')
    parser.add_argument('--export', help='Export forecast to CSV file')

    args = parser.parse_args()

    # Load data
    df = load_data(args.input)

    # Train model
    model = train_prophet_model(df, args.seasonality)

    # Generate forecast
    forecast = generate_forecast(model, df, args.forecast_days)

    # Capacity analysis
    capacity_analysis(df, forecast, args.forecast_days)

    # Visualize
    if args.visualize:
        visualize_forecast(model, df, forecast)

    # Export
    if args.export:
        export_forecast(forecast, args.forecast_days, args.export)


if __name__ == '__main__':
    main()
