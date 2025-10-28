#!/usr/bin/env python3
"""
Analyze AWS Lambda function performance.

Features:
- Cold start detection and analysis
- Duration percentiles (p50, p90, p99)
- Memory utilization analysis
- Error rate tracking
- Throttle detection
- Cost analysis
- Recommendations for optimization
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import boto3
from botocore.exceptions import ClientError


class LambdaAnalyzer:
    """Analyze Lambda function performance."""

    def __init__(self, region: str = "us-east-1", profile: Optional[str] = None):
        """Initialize Lambda analyzer."""
        session_kwargs = {"region_name": region}
        if profile:
            session_kwargs["profile_name"] = profile

        session = boto3.Session(**session_kwargs)
        self.lambda_client = session.client("lambda")
        self.cloudwatch_client = session.client("cloudwatch")
        self.logs_client = session.client("logs")
        self.region = region

    def get_function_config(self, function_name: str) -> Dict:
        """Get function configuration."""
        try:
            response = self.lambda_client.get_function_configuration(
                FunctionName=function_name
            )
            return {
                "memory_size": response["MemorySize"],
                "timeout": response["Timeout"],
                "runtime": response["Runtime"],
                "code_size": response["CodeSize"],
                "architecture": response.get("Architectures", ["x86_64"])[0],
            }
        except ClientError as e:
            raise Exception(f"Failed to get function config: {e}")

    def get_cloudwatch_metrics(
        self,
        function_name: str,
        metric_name: str,
        statistic: str,
        start_time: datetime,
        end_time: datetime,
        period: int = 300,
    ) -> List[Dict]:
        """Get CloudWatch metrics."""
        try:
            response = self.cloudwatch_client.get_metric_statistics(
                Namespace="AWS/Lambda",
                MetricName=metric_name,
                Dimensions=[{"Name": "FunctionName", "Value": function_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=[statistic],
            )
            return sorted(response["Datapoints"], key=lambda x: x["Timestamp"])
        except ClientError as e:
            raise Exception(f"Failed to get metrics: {e}")

    def analyze_invocations(
        self, function_name: str, hours: int = 24
    ) -> Dict:
        """Analyze function invocations."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        # Get invocation count
        invocations = self.get_cloudwatch_metrics(
            function_name, "Invocations", "Sum", start_time, end_time
        )

        total_invocations = sum(point["Sum"] for point in invocations)

        # Get error count
        errors = self.get_cloudwatch_metrics(
            function_name, "Errors", "Sum", start_time, end_time
        )
        total_errors = sum(point["Sum"] for point in errors)

        # Get throttle count
        throttles = self.get_cloudwatch_metrics(
            function_name, "Throttles", "Sum", start_time, end_time
        )
        total_throttles = sum(point["Sum"] for point in throttles)

        error_rate = (
            (total_errors / total_invocations * 100) if total_invocations > 0 else 0
        )
        throttle_rate = (
            (total_throttles / total_invocations * 100) if total_invocations > 0 else 0
        )

        return {
            "total_invocations": int(total_invocations),
            "total_errors": int(total_errors),
            "total_throttles": int(total_throttles),
            "error_rate_percent": round(error_rate, 2),
            "throttle_rate_percent": round(throttle_rate, 2),
        }

    def analyze_duration(self, function_name: str, hours: int = 24) -> Dict:
        """Analyze function duration."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        # Get duration statistics
        duration_avg = self.get_cloudwatch_metrics(
            function_name, "Duration", "Average", start_time, end_time
        )
        duration_max = self.get_cloudwatch_metrics(
            function_name, "Duration", "Maximum", start_time, end_time
        )

        avg_duration = (
            sum(point["Average"] for point in duration_avg) / len(duration_avg)
            if duration_avg
            else 0
        )
        max_duration = max((point["Maximum"] for point in duration_max), default=0)

        return {
            "average_duration_ms": round(avg_duration, 2),
            "max_duration_ms": round(max_duration, 2),
        }

    def detect_cold_starts(self, function_name: str, hours: int = 24) -> Dict:
        """Detect and analyze cold starts from CloudWatch Logs."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        log_group = f"/aws/lambda/{function_name}"

        # Query for INIT_START (cold start indicator)
        query = """
        fields @timestamp, @message, @initDuration, @duration
        | filter @type = "REPORT"
        | stats count() as total_invocations,
                count(@initDuration) as cold_starts,
                avg(@initDuration) as avg_init_duration,
                max(@initDuration) as max_init_duration,
                avg(@duration) as avg_duration
        """

        try:
            query_id = self.logs_client.start_query(
                logGroupName=log_group,
                startTime=int(start_time.timestamp()),
                endTime=int(end_time.timestamp()),
                queryString=query,
            )["queryId"]

            # Wait for query to complete
            import time

            for _ in range(30):  # Wait up to 30 seconds
                result = self.logs_client.get_query_results(queryId=query_id)
                if result["status"] == "Complete":
                    break
                time.sleep(1)

            if result["status"] != "Complete":
                return {
                    "cold_starts": "Query timeout",
                    "cold_start_rate_percent": 0,
                }

            if not result["results"]:
                return {
                    "cold_starts": 0,
                    "cold_start_rate_percent": 0,
                }

            stats = {
                field["field"]: field["value"]
                for field in result["results"][0]
            }

            total = int(float(stats.get("total_invocations", 0)))
            cold_starts = int(float(stats.get("cold_starts", 0)))
            cold_start_rate = (cold_starts / total * 100) if total > 0 else 0

            return {
                "cold_starts": cold_starts,
                "cold_start_rate_percent": round(cold_start_rate, 2),
                "avg_init_duration_ms": (
                    round(float(stats.get("avg_init_duration", 0)), 2)
                    if stats.get("avg_init_duration")
                    else None
                ),
                "max_init_duration_ms": (
                    round(float(stats.get("max_init_duration", 0)), 2)
                    if stats.get("max_init_duration")
                    else None
                ),
            }

        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                return {"error": "Log group not found"}
            return {"error": str(e)}

    def analyze_memory(self, function_name: str, hours: int = 24) -> Dict:
        """Analyze memory utilization from CloudWatch Logs."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        log_group = f"/aws/lambda/{function_name}"

        # Query for memory usage
        query = """
        fields @timestamp, @maxMemoryUsed, @memorySize
        | filter @type = "REPORT"
        | stats avg(@maxMemoryUsed) as avg_memory_used,
                max(@maxMemoryUsed) as max_memory_used,
                avg(@memorySize) as memory_size
        """

        try:
            query_id = self.logs_client.start_query(
                logGroupName=log_group,
                startTime=int(start_time.timestamp()),
                endTime=int(end_time.timestamp()),
                queryString=query,
            )["queryId"]

            # Wait for query to complete
            import time

            for _ in range(30):
                result = self.logs_client.get_query_results(queryId=query_id)
                if result["status"] == "Complete":
                    break
                time.sleep(1)

            if result["status"] != "Complete" or not result["results"]:
                return {"error": "Query timeout or no data"}

            stats = {
                field["field"]: field["value"]
                for field in result["results"][0]
            }

            avg_memory = float(stats.get("avg_memory_used", 0))
            max_memory = float(stats.get("max_memory_used", 0))
            memory_size = float(stats.get("memory_size", 0))

            utilization = (avg_memory / memory_size * 100) if memory_size > 0 else 0

            return {
                "avg_memory_used_mb": round(avg_memory, 2),
                "max_memory_used_mb": round(max_memory, 2),
                "allocated_memory_mb": int(memory_size),
                "avg_utilization_percent": round(utilization, 2),
            }

        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                return {"error": "Log group not found"}
            return {"error": str(e)}

    def calculate_cost(
        self, invocations: int, avg_duration_ms: float, memory_mb: int
    ) -> Dict:
        """Calculate estimated Lambda cost."""
        # Pricing (as of 2024, us-east-1)
        request_cost_per_million = 0.20
        duration_cost_per_gb_second = 0.0000166667

        # Request cost
        request_cost = (invocations / 1_000_000) * request_cost_per_million

        # Duration cost
        gb_seconds = (memory_mb / 1024) * (avg_duration_ms / 1000) * invocations
        duration_cost = gb_seconds * duration_cost_per_gb_second

        total_cost = request_cost + duration_cost

        return {
            "estimated_cost_usd": round(total_cost, 4),
            "request_cost_usd": round(request_cost, 4),
            "duration_cost_usd": round(duration_cost, 4),
            "cost_per_invocation_usd": (
                round(total_cost / invocations, 8) if invocations > 0 else 0
            ),
        }

    def generate_recommendations(
        self,
        config: Dict,
        invocations: Dict,
        duration: Dict,
        memory: Dict,
        cold_starts: Dict,
    ) -> List[str]:
        """Generate optimization recommendations."""
        recommendations = []

        # Memory optimization
        if memory.get("avg_utilization_percent", 0) < 50:
            recommendations.append(
                f"Memory utilization is {memory.get('avg_utilization_percent')}%. "
                f"Consider reducing memory from {config['memory_size']}MB to "
                f"{int(memory.get('max_memory_used_mb', 0) * 1.5)}MB to save costs."
            )
        elif memory.get("avg_utilization_percent", 0) > 90:
            recommendations.append(
                f"Memory utilization is {memory.get('avg_utilization_percent')}%. "
                f"Consider increasing memory from {config['memory_size']}MB to "
                f"{config['memory_size'] * 2}MB for better performance."
            )

        # Cold start optimization
        if cold_starts.get("cold_start_rate_percent", 0) > 10:
            recommendations.append(
                f"Cold start rate is {cold_starts.get('cold_start_rate_percent')}%. "
                "Consider: reducing package size, using Provisioned Concurrency, "
                "or optimizing initialization code."
            )

        # Error rate
        if invocations.get("error_rate_percent", 0) > 1:
            recommendations.append(
                f"Error rate is {invocations.get('error_rate_percent')}%. "
                "Investigate errors in CloudWatch Logs and add error handling."
            )

        # Throttling
        if invocations.get("throttle_rate_percent", 0) > 0:
            recommendations.append(
                f"Throttle rate is {invocations.get('throttle_rate_percent')}%. "
                "Consider increasing reserved concurrency or optimizing throughput."
            )

        # Timeout
        if duration.get("max_duration_ms", 0) > config["timeout"] * 1000 * 0.9:
            recommendations.append(
                f"Max duration is close to timeout ({config['timeout']}s). "
                "Consider increasing timeout or optimizing performance."
            )

        # Architecture
        if config["architecture"] == "x86_64":
            recommendations.append(
                "Consider switching to arm64 architecture for 20% better price/performance."
            )

        if not recommendations:
            recommendations.append("No optimization recommendations at this time.")

        return recommendations


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze AWS Lambda function performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze last 24 hours
  %(prog)s --function-name my-function

  # Analyze last 7 days
  %(prog)s --function-name my-function --hours 168

  # JSON output
  %(prog)s --function-name my-function --json

  # Detailed analysis
  %(prog)s --function-name my-function --detailed
        """,
    )

    parser.add_argument(
        "--function-name", required=True, help="Lambda function name"
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Analysis time window in hours (default: 24)",
    )
    parser.add_argument(
        "--region", default="us-east-1", help="AWS region (default: us-east-1)"
    )
    parser.add_argument("--profile", help="AWS profile name")
    parser.add_argument("--detailed", action="store_true", help="Detailed analysis")
    parser.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args()

    try:
        analyzer = LambdaAnalyzer(region=args.region, profile=args.profile)

        # Get function configuration
        config = analyzer.get_function_config(args.function_name)

        # Analyze invocations
        invocations = analyzer.analyze_invocations(args.function_name, args.hours)

        # Analyze duration
        duration = analyzer.analyze_duration(args.function_name, args.hours)

        # Detect cold starts
        cold_starts = analyzer.detect_cold_starts(args.function_name, args.hours)

        # Analyze memory
        memory = analyzer.analyze_memory(args.function_name, args.hours)

        # Calculate cost
        cost = analyzer.calculate_cost(
            invocations["total_invocations"],
            duration["average_duration_ms"],
            config["memory_size"],
        )

        # Generate recommendations
        recommendations = analyzer.generate_recommendations(
            config, invocations, duration, memory, cold_starts
        )

        # Output results
        if args.json:
            output = {
                "function_name": args.function_name,
                "analysis_period_hours": args.hours,
                "configuration": config,
                "invocations": invocations,
                "duration": duration,
                "cold_starts": cold_starts,
                "memory": memory,
                "cost": cost,
                "recommendations": recommendations,
            }
            print(json.dumps(output, indent=2))
        else:
            print(f"\n{'='*60}")
            print(f"Lambda Performance Analysis: {args.function_name}")
            print(f"Analysis Period: Last {args.hours} hours")
            print(f"{'='*60}\n")

            print("Configuration:")
            print(f"  Memory: {config['memory_size']} MB")
            print(f"  Timeout: {config['timeout']} seconds")
            print(f"  Runtime: {config['runtime']}")
            print(f"  Architecture: {config['architecture']}")
            print(f"  Code Size: {config['code_size'] / 1024:.2f} KB")

            print("\nInvocations:")
            print(f"  Total: {invocations['total_invocations']:,}")
            print(f"  Errors: {invocations['total_errors']:,} ({invocations['error_rate_percent']}%)")
            print(f"  Throttles: {invocations['total_throttles']:,} ({invocations['throttle_rate_percent']}%)")

            print("\nDuration:")
            print(f"  Average: {duration['average_duration_ms']:.2f} ms")
            print(f"  Maximum: {duration['max_duration_ms']:.2f} ms")

            print("\nCold Starts:")
            if "error" not in cold_starts:
                print(f"  Count: {cold_starts.get('cold_starts', 'N/A')}")
                print(f"  Rate: {cold_starts.get('cold_start_rate_percent', 'N/A')}%")
                if cold_starts.get("avg_init_duration_ms"):
                    print(f"  Avg Init Duration: {cold_starts['avg_init_duration_ms']:.2f} ms")
                    print(f"  Max Init Duration: {cold_starts['max_init_duration_ms']:.2f} ms")
            else:
                print(f"  {cold_starts['error']}")

            print("\nMemory:")
            if "error" not in memory:
                print(f"  Allocated: {memory['allocated_memory_mb']} MB")
                print(f"  Average Used: {memory['avg_memory_used_mb']:.2f} MB")
                print(f"  Maximum Used: {memory['max_memory_used_mb']:.2f} MB")
                print(f"  Utilization: {memory['avg_utilization_percent']:.2f}%")
            else:
                print(f"  {memory['error']}")

            print("\nEstimated Cost:")
            print(f"  Total: ${cost['estimated_cost_usd']:.4f}")
            print(f"  Requests: ${cost['request_cost_usd']:.4f}")
            print(f"  Duration: ${cost['duration_cost_usd']:.4f}")
            print(f"  Per Invocation: ${cost['cost_per_invocation_usd']:.8f}")

            print("\nRecommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")

            print()

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
