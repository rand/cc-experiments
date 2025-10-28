"""
Basic Lambda function example.

This is the simplest Lambda function that returns a JSON response.
"""

import json


def lambda_handler(event, context):
    """
    Basic Lambda handler.

    Args:
        event: Event data passed to the function
        context: Runtime information

    Returns:
        Response with status code and body
    """
    print(f"Request ID: {context.aws_request_id}")
    print(f"Function name: {context.function_name}")
    print(f"Event: {json.dumps(event)}")

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps({
            "message": "Hello from Lambda!",
            "request_id": context.aws_request_id,
            "remaining_time_ms": context.get_remaining_time_in_millis(),
        }),
    }
