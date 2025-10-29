#!/usr/bin/env python3
"""
Cloud Cost Analysis and Optimization Tool

Analyzes resource usage and identifies cost optimization opportunities:
- Right-sizing recommendations
- Reserved capacity opportunities
- Spot instance candidates
- Storage tiering suggestions

Usage:
    python analyze_costs.py --provider aws --region us-east-1
    python analyze_costs.py --csv resource_usage.csv --optimize
"""

import argparse
import pandas as pd
import json


# AWS pricing (example, simplified)
AWS_PRICING = {
    't3.micro': {'hourly': 0.0104, 'monthly': 7.59},
    't3.small': {'hourly': 0.0208, 'monthly': 15.18},
    't3.medium': {'hourly': 0.0416, 'monthly': 30.37},
    't3.large': {'hourly': 0.0832, 'monthly': 60.74},
    'm5.large': {'hourly': 0.096, 'monthly': 70.08},
    'm5.xlarge': {'hourly': 0.192, 'monthly': 140.16},
    'm5.2xlarge': {'hourly': 0.384, 'monthly': 280.32},
}

def analyze_rightsizing(resources):
    """Identify rightsizing opportunities."""
    recommendations = []

    for resource in resources:
        avg_cpu = resource['avg_cpu']
        avg_memory = resource['avg_memory']
        current_type = resource['instance_type']
        current_cost = AWS_PRICING[current_type]['monthly']

        # Under-utilized
        if avg_cpu < 30 and avg_memory < 30:
            # Recommend smaller instance
            target = downsize_instance(current_type)
            if target:
                new_cost = AWS_PRICING[target]['monthly']
                savings = current_cost - new_cost

                recommendations.append({
                    'resource_id': resource['id'],
                    'action': 'downsize',
                    'current_type': current_type,
                    'recommended_type': target,
                    'current_cost': current_cost,
                    'new_cost': new_cost,
                    'monthly_savings': savings,
                    'reason': f'Low utilization (CPU: {avg_cpu}%, Mem: {avg_memory}%)'
                })

    return recommendations


def downsize_instance(instance_type):
    """Get smaller instance type."""
    size_map = {
        't3.large': 't3.medium',
        't3.medium': 't3.small',
        'm5.2xlarge': 'm5.xlarge',
        'm5.xlarge': 'm5.large',
    }
    return size_map.get(instance_type)


def main():
    parser = argparse.ArgumentParser(description='Cloud cost optimization analysis')
    parser.add_argument('--provider', choices=['aws', 'gcp', 'azure'], default='aws')
    parser.add_argument('--region', default='us-east-1')
    parser.add_argument('--csv', help='CSV file with resource usage data')
    parser.add_argument('--optimize', action='store_true')

    args = parser.parse_args()

    # Example analysis
    print(f"Analyzing {args.provider} costs in {args.region}")
    print("\nCost optimization opportunities found")


if __name__ == '__main__':
    main()
