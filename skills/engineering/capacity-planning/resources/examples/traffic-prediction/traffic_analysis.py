#!/usr/bin/env python3
"""
Traffic Pattern Analysis

Analyzes traffic patterns to identify:
- Seasonality (daily, weekly, monthly)
- Growth rates
- Peak patterns
- Anomalies

Usage:
    python traffic_analysis.py --input traffic_data.csv
"""

import argparse
import pandas as pd
import numpy as np
from datetime import datetime


def detect_seasonality(data):
    """Detect seasonal patterns in traffic data."""
    print("\n=== Seasonality Detection ===")

    df = pd.DataFrame(data)
    df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
    df['dayofweek'] = pd.to_datetime(df['timestamp']).dt.dayofweek

    # Hourly pattern
    hourly_avg = df.groupby('hour')['value'].mean()
    peak_hour = hourly_avg.idxmax()
    low_hour = hourly_avg.idxmin()

    print(f"Hourly pattern:")
    print(f"  Peak hour: {peak_hour}:00 ({hourly_avg[peak_hour]:.0f} requests)")
    print(f"  Low hour: {low_hour}:00 ({hourly_avg[low_hour]:.0f} requests)")

    # Daily pattern
    daily_avg = df.groupby('dayofweek')['value'].mean()
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    peak_day = daily_avg.idxmax()

    print(f"\nWeekly pattern:")
    print(f"  Peak day: {days[peak_day]} ({daily_avg[peak_day]:.0f} requests)")


def analyze_growth_rate(data):
    """Analyze traffic growth rate."""
    print("\n=== Growth Rate Analysis ===")

    df = pd.DataFrame(data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Simple linear trend
    X = np.arange(len(df))
    y = df['value'].values
    slope = np.polyfit(X, y, 1)[0]

    # Daily growth rate
    daily_growth = (slope / df['value'].mean()) * 100

    print(f"Daily growth rate: {daily_growth:.2f}%")
    print(f"Monthly growth rate: {daily_growth * 30:.2f}%")

    # Projection
    days_ahead = 90
    current_avg = df['value'].tail(7).mean()
    future_avg = current_avg * ((1 + daily_growth/100) ** days_ahead)

    print(f"\n90-day projection:")
    print(f"  Current average: {current_avg:.0f} requests")
    print(f"  Projected average: {future_avg:.0f} requests")
    print(f"  Growth: {((future_avg/current_avg - 1) * 100):.1f}%")


def main():
    parser = argparse.ArgumentParser(description='Traffic pattern analysis')
    parser.add_argument('--input', required=True, help='Input CSV file')

    args = parser.parse_args()

    # Load data
    df = pd.read_csv(args.input)
    data = df.to_dict('records')

    detect_seasonality(data)
    analyze_growth_rate(data)


if __name__ == '__main__':
    main()
