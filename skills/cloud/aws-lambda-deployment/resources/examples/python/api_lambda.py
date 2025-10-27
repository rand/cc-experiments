"""
API Gateway Lambda integration example.

Handles HTTP requests from API Gateway with routing, validation, and error handling.
"""

import json
import os
from typing import Dict, Any


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    API Gateway proxy integration handler.

    Args:
        event: API Gateway proxy event
        context: Lambda context

    Returns:
        API Gateway response
    """
    try:
        # Parse request
        http_method = event.get("httpMethod")
        path = event.get("path")
        query_params = event.get("queryStringParameters") or {}
        headers = event.get("headers") or {}
        body = event.get("body")

        # Parse body if present
        request_body = None
        if body:
            try:
                request_body = json.loads(body)
            except json.JSONDecodeError:
                return error_response(400, "Invalid JSON in request body")

        # Route based on method and path
        if http_method == "GET" and path == "/items":
            return get_items(query_params)
        elif http_method == "POST" and path == "/items":
            return create_item(request_body)
        elif http_method == "GET" and path.startswith("/items/"):
            item_id = path.split("/")[-1]
            return get_item(item_id)
        elif http_method == "PUT" and path.startswith("/items/"):
            item_id = path.split("/")[-1]
            return update_item(item_id, request_body)
        elif http_method == "DELETE" and path.startswith("/items/"):
            item_id = path.split("/")[-1]
            return delete_item(item_id)
        else:
            return error_response(404, "Not Found")

    except Exception as e:
        print(f"Error: {str(e)}")
        return error_response(500, "Internal Server Error")


def get_items(query_params: Dict[str, str]) -> Dict[str, Any]:
    """Get list of items."""
    limit = int(query_params.get("limit", 10))
    offset = int(query_params.get("offset", 0))

    # Mock data (replace with actual database query)
    items = [
        {"id": f"item-{i}", "name": f"Item {i}", "price": i * 10.0}
        for i in range(offset, offset + limit)
    ]

    return success_response({
        "items": items,
        "limit": limit,
        "offset": offset,
        "total": 100,  # Mock total
    })


def get_item(item_id: str) -> Dict[str, Any]:
    """Get single item."""
    # Mock data (replace with actual database query)
    if not item_id:
        return error_response(400, "Missing item ID")

    item = {
        "id": item_id,
        "name": f"Item {item_id}",
        "price": 99.99,
        "description": "Sample item",
    }

    return success_response(item)


def create_item(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create new item."""
    if not data:
        return error_response(400, "Missing request body")

    # Validate required fields
    if "name" not in data:
        return error_response(400, "Missing required field: name")
    if "price" not in data:
        return error_response(400, "Missing required field: price")

    # Mock creation (replace with actual database insert)
    item = {
        "id": f"item-{hash(data['name'])}",
        "name": data["name"],
        "price": data["price"],
        "description": data.get("description", ""),
    }

    return success_response(item, status_code=201)


def update_item(item_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update existing item."""
    if not item_id:
        return error_response(400, "Missing item ID")
    if not data:
        return error_response(400, "Missing request body")

    # Mock update (replace with actual database update)
    item = {
        "id": item_id,
        "name": data.get("name", f"Item {item_id}"),
        "price": data.get("price", 99.99),
        "description": data.get("description", ""),
    }

    return success_response(item)


def delete_item(item_id: str) -> Dict[str, Any]:
    """Delete item."""
    if not item_id:
        return error_response(400, "Missing item ID")

    # Mock deletion (replace with actual database delete)

    return success_response({"message": f"Item {item_id} deleted"})


def success_response(data: Any, status_code: int = 200) -> Dict[str, Any]:
    """Create success response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        },
        "body": json.dumps(data),
    }


def error_response(status_code: int, message: str) -> Dict[str, Any]:
    """Create error response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps({"error": message}),
    }
