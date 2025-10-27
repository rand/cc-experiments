#!/usr/bin/env python3
"""
OpenAPI Generator

Generate OpenAPI specifications from code or convert between formats.
Supports:
- Python (FastAPI, Flask)
- Node.js (Express)
- OpenAPI 2.0 to 3.0 conversion
- Code generation from OpenAPI specs
"""

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


class OpenAPIGenerator:
    """Generate OpenAPI specifications"""

    def __init__(self):
        self.spec: Dict[str, Any] = {
            "openapi": "3.0.0",
            "info": {
                "title": "API",
                "version": "1.0.0",
                "description": "Generated API documentation"
            },
            "paths": {},
            "components": {
                "schemas": {},
                "securitySchemes": {}
            }
        }

    def from_fastapi(self, code: str) -> Dict[str, Any]:
        """Generate OpenAPI from FastAPI code"""
        tree = ast.parse(code)

        # Find FastAPI app
        app_name = self._find_fastapi_app(tree)
        if not app_name:
            raise ValueError("No FastAPI app found")

        # Extract routes
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check for route decorators
                for decorator in node.decorator_list:
                    route_info = self._parse_fastapi_decorator(decorator, app_name)
                    if route_info:
                        path, method = route_info
                        self._add_endpoint(path, method, node)

        return self.spec

    def from_flask(self, code: str) -> Dict[str, Any]:
        """Generate OpenAPI from Flask code"""
        tree = ast.parse(code)

        # Find Flask app
        app_name = self._find_flask_app(tree)
        if not app_name:
            raise ValueError("No Flask app found")

        # Extract routes
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check for route decorators
                for decorator in node.decorator_list:
                    route_info = self._parse_flask_decorator(decorator, app_name)
                    if route_info:
                        path, methods = route_info
                        for method in methods:
                            self._add_endpoint(path, method, node)

        return self.spec

    def from_express(self, code: str) -> Dict[str, Any]:
        """Generate OpenAPI from Express.js code"""
        # Parse Express route definitions
        # Pattern: app.METHOD(path, handler)
        patterns = [
            r"app\.(get|post|put|patch|delete)\(['\"]([^'\"]+)['\"]",
            r"router\.(get|post|put|patch|delete)\(['\"]([^'\"]+)['\"]"
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, code)
            for match in matches:
                method = match.group(1).upper()
                path = match.group(2)
                self._add_endpoint(path, method, None)

        return self.spec

    def convert_swagger_to_openapi(self, swagger: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Swagger 2.0 to OpenAPI 3.0"""
        # Basic conversion
        self.spec["info"] = swagger.get("info", {})

        # Convert host/basePath to servers
        host = swagger.get("host", "")
        base_path = swagger.get("basePath", "")
        schemes = swagger.get("schemes", ["https"])

        self.spec["servers"] = [
            {"url": f"{schemes[0]}://{host}{base_path}"}
        ]

        # Convert paths
        for path, methods in swagger.get("paths", {}).items():
            self.spec["paths"][path] = {}

            for method, details in methods.items():
                if method in ["get", "post", "put", "patch", "delete"]:
                    self.spec["paths"][path][method] = self._convert_operation(details)

        # Convert definitions to schemas
        definitions = swagger.get("definitions", {})
        for name, schema in definitions.items():
            self.spec["components"]["schemas"][name] = schema

        # Convert security definitions
        security_defs = swagger.get("securityDefinitions", {})
        for name, sec_def in security_defs.items():
            self.spec["components"]["securitySchemes"][name] = self._convert_security(sec_def)

        return self.spec

    def _find_fastapi_app(self, tree: ast.AST) -> Optional[str]:
        """Find FastAPI app variable name"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.Call):
                    if hasattr(node.value.func, 'id') and node.value.func.id == 'FastAPI':
                        if isinstance(node.targets[0], ast.Name):
                            return node.targets[0].id
        return None

    def _find_flask_app(self, tree: ast.AST) -> Optional[str]:
        """Find Flask app variable name"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.Call):
                    if hasattr(node.value.func, 'id') and node.value.func.id == 'Flask':
                        if isinstance(node.targets[0], ast.Name):
                            return node.targets[0].id
        return None

    def _parse_fastapi_decorator(self, decorator: ast.AST, app_name: str) -> Optional[tuple]:
        """Parse FastAPI route decorator"""
        if isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Attribute):
                if isinstance(decorator.func.value, ast.Name):
                    if decorator.func.value.id == app_name:
                        method = decorator.func.attr.upper()
                        if decorator.args and isinstance(decorator.args[0], ast.Constant):
                            path = decorator.args[0].value
                            return (path, method)
        return None

    def _parse_flask_decorator(self, decorator: ast.AST, app_name: str) -> Optional[tuple]:
        """Parse Flask route decorator"""
        if isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Attribute):
                if isinstance(decorator.func.value, ast.Name):
                    if decorator.func.value.id == app_name and decorator.func.attr == "route":
                        if decorator.args and isinstance(decorator.args[0], ast.Constant):
                            path = decorator.args[0].value
                            methods = ["GET"]  # Default

                            # Check for methods kwarg
                            for keyword in decorator.keywords:
                                if keyword.arg == "methods":
                                    if isinstance(keyword.value, ast.List):
                                        methods = [
                                            elt.value for elt in keyword.value.elts
                                            if isinstance(elt, ast.Constant)
                                        ]

                            return (path, methods)
        return None

    def _add_endpoint(self, path: str, method: str, func_node: Optional[ast.FunctionDef]):
        """Add endpoint to OpenAPI spec"""
        if path not in self.spec["paths"]:
            self.spec["paths"][path] = {}

        # Extract docstring and parameters from function
        summary = ""
        description = ""
        parameters = []
        request_body = None
        responses = {"200": {"description": "Successful response"}}

        if func_node:
            # Extract docstring
            docstring = ast.get_docstring(func_node)
            if docstring:
                lines = docstring.strip().split("\n")
                summary = lines[0] if lines else ""
                description = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""

            # Extract parameters
            for arg in func_node.args.args:
                if arg.arg not in ["self", "cls", "request", "response"]:
                    param = {
                        "name": arg.arg,
                        "in": "path" if f"{{{arg.arg}}}" in path else "query",
                        "required": f"{{{arg.arg}}}" in path,
                        "schema": {"type": "string"}
                    }
                    parameters.append(param)

            # Check for request body (POST, PUT, PATCH)
            if method in ["POST", "PUT", "PATCH"]:
                request_body = {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"type": "object"}
                        }
                    }
                }

        self.spec["paths"][path][method.lower()] = {
            "summary": summary or f"{method} {path}",
            "description": description,
            "parameters": parameters,
            "responses": responses
        }

        if request_body:
            self.spec["paths"][path][method.lower()]["requestBody"] = request_body

    def _convert_operation(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Swagger operation to OpenAPI"""
        converted = {
            "summary": operation.get("summary", ""),
            "description": operation.get("description", ""),
            "parameters": [],
            "responses": {}
        }

        # Convert parameters
        for param in operation.get("parameters", []):
            if param.get("in") == "body":
                # Convert to requestBody
                converted["requestBody"] = {
                    "required": param.get("required", False),
                    "content": {
                        "application/json": {
                            "schema": param.get("schema", {})
                        }
                    }
                }
            else:
                # Regular parameter
                converted_param = {
                    "name": param["name"],
                    "in": param["in"],
                    "required": param.get("required", False),
                    "schema": {
                        "type": param.get("type", "string")
                    }
                }
                if "description" in param:
                    converted_param["description"] = param["description"]
                converted["parameters"].append(converted_param)

        # Convert responses
        for status, response in operation.get("responses", {}).items():
            converted["responses"][status] = {
                "description": response.get("description", "")
            }

            if "schema" in response:
                converted["responses"][status]["content"] = {
                    "application/json": {
                        "schema": response["schema"]
                    }
                }

        return converted

    def _convert_security(self, sec_def: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Swagger security definition to OpenAPI"""
        sec_type = sec_def.get("type", "")

        if sec_type == "basic":
            return {
                "type": "http",
                "scheme": "basic"
            }
        elif sec_type == "apiKey":
            return {
                "type": "apiKey",
                "in": sec_def.get("in", "header"),
                "name": sec_def.get("name", "api_key")
            }
        elif sec_type == "oauth2":
            return {
                "type": "oauth2",
                "flows": {
                    "authorizationCode": {
                        "authorizationUrl": sec_def.get("authorizationUrl", ""),
                        "tokenUrl": sec_def.get("tokenUrl", ""),
                        "scopes": sec_def.get("scopes", {})
                    }
                }
            }

        return sec_def


def generate_client_code(spec: Dict[str, Any], language: str) -> str:
    """Generate client code from OpenAPI spec"""
    if language == "python":
        return generate_python_client(spec)
    elif language == "javascript":
        return generate_javascript_client(spec)
    elif language == "typescript":
        return generate_typescript_client(spec)
    else:
        raise ValueError(f"Unsupported language: {language}")


def generate_python_client(spec: Dict[str, Any]) -> str:
    """Generate Python client code"""
    code = '''"""
API Client

Auto-generated from OpenAPI specification
"""

import requests
from typing import Any, Dict, Optional


class APIClient:
    """API client"""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()

        if api_key:
            self.session.headers["Authorization"] = f"Bearer {api_key}"

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Make HTTP request"""
        url = f"{self.base_url}{path}"
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response

'''

    # Generate methods for each endpoint
    for path, methods in spec.get("paths", {}).items():
        for method, details in methods.items():
            if method.lower() in ["get", "post", "put", "patch", "delete"]:
                code += generate_python_method(path, method, details)

    return code


def generate_python_method(path: str, method: str, details: Dict[str, Any]) -> str:
    """Generate Python method for endpoint"""
    # Create method name from path
    method_name = path.strip("/").replace("/", "_").replace("{", "").replace("}", "").replace("-", "_")
    if not method_name:
        method_name = "root"

    method_name = f"{method.lower()}_{method_name}"

    # Extract parameters
    params = details.get("parameters", [])
    path_params = [p["name"] for p in params if p.get("in") == "path"]
    query_params = [p["name"] for p in params if p.get("in") == "query"]

    # Build function signature
    args = ["self"]
    args.extend(path_params)

    if method.upper() in ["POST", "PUT", "PATCH"]:
        args.append("data: Dict[str, Any]")

    for param in query_params:
        args.append(f'{param}: Optional[Any] = None')

    summary = details.get("summary", "")

    code = f'''
    def {method_name}({", ".join(args)}) -> Dict[str, Any]:
        """{summary}"""
        path = "{path}"
'''

    # Replace path parameters
    for param in path_params:
        code += f'        path = path.replace("{{{param}}}", str({param}))\n'

    # Add query parameters
    if query_params:
        code += '        params = {}\n'
        for param in query_params:
            code += f'        if {param} is not None:\n'
            code += f'            params["{param}"] = {param}\n'

    # Make request
    if method.upper() in ["POST", "PUT", "PATCH"]:
        if query_params:
            code += f'        response = self._request("{method.upper()}", path, json=data, params=params)\n'
        else:
            code += f'        response = self._request("{method.upper()}", path, json=data)\n'
    else:
        if query_params:
            code += f'        response = self._request("{method.upper()}", path, params=params)\n'
        else:
            code += f'        response = self._request("{method.upper()}", path)\n'

    code += '        return response.json()\n'

    return code


def generate_javascript_client(spec: Dict[str, Any]) -> str:
    """Generate JavaScript client code"""
    code = '''/**
 * API Client
 *
 * Auto-generated from OpenAPI specification
 */

class APIClient {
  constructor(baseUrl, apiKey = null) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.apiKey = apiKey;
  }

  async _request(method, path, options = {}) {
    const url = `${this.baseUrl}${path}`;
    const headers = options.headers || {};

    if (this.apiKey) {
      headers['Authorization'] = `Bearer ${this.apiKey}`;
    }

    if (options.json) {
      headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(url, {
      method,
      headers,
      body: options.json ? JSON.stringify(options.json) : options.body
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

'''

    # Generate methods for each endpoint
    for path, methods in spec.get("paths", {}).items():
        for method, details in methods.items():
            if method.lower() in ["get", "post", "put", "patch", "delete"]:
                code += generate_javascript_method(path, method, details)

    code += "}\n\nmodule.exports = APIClient;\n"

    return code


def generate_javascript_method(path: str, method: str, details: Dict[str, Any]) -> str:
    """Generate JavaScript method for endpoint"""
    method_name = path.strip("/").replace("/", "_").replace("{", "").replace("}", "").replace("-", "_")
    if not method_name:
        method_name = "root"

    method_name = f"{method.lower()}_{method_name}"

    params = details.get("parameters", [])
    path_params = [p["name"] for p in params if p.get("in") == "path"]
    query_params = [p["name"] for p in params if p.get("in") == "query"]

    args = []
    args.extend(path_params)

    if method.upper() in ["POST", "PUT", "PATCH"]:
        args.append("data")

    if query_params:
        args.append("options = {}")

    summary = details.get("summary", "")

    code = f'''
  /**
   * {summary}
   */
  async {method_name}({", ".join(args)}) {{
    let path = "{path}";
'''

    # Replace path parameters
    for param in path_params:
        code += f'    path = path.replace("{{{param}}}", {param});\n'

    # Add query parameters
    if query_params:
        code += '    const params = new URLSearchParams();\n'
        for param in query_params:
            code += f'    if (options.{param}) params.append("{param}", options.{param});\n'
        code += '    if (params.toString()) path += `?${params.toString()}`;\n'

    # Make request
    if method.upper() in ["POST", "PUT", "PATCH"]:
        code += f'    return this._request("{method.upper()}", path, {{ json: data }});\n'
    else:
        code += f'    return this._request("{method.upper()}", path);\n'

    code += '  }\n'

    return code


def generate_typescript_client(spec: Dict[str, Any]) -> str:
    """Generate TypeScript client code"""
    # Similar to JavaScript but with type annotations
    return generate_javascript_client(spec).replace(
        "class APIClient",
        "export class APIClient"
    )


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Generate OpenAPI specifications or client code"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # Generate spec from code
    gen_parser = subparsers.add_parser("from-code", help="Generate OpenAPI from code")
    gen_parser.add_argument("input", help="Source code file")
    gen_parser.add_argument("--framework", choices=["fastapi", "flask", "express"], required=True)
    gen_parser.add_argument("--output", "-o", help="Output file (default: stdout)")

    # Convert Swagger to OpenAPI
    conv_parser = subparsers.add_parser("convert", help="Convert Swagger 2.0 to OpenAPI 3.0")
    conv_parser.add_argument("input", help="Swagger 2.0 specification file")
    conv_parser.add_argument("--output", "-o", help="Output file (default: stdout)")

    # Generate client code
    client_parser = subparsers.add_parser("generate-client", help="Generate client code from OpenAPI")
    client_parser.add_argument("input", help="OpenAPI specification file")
    client_parser.add_argument("--language", choices=["python", "javascript", "typescript"], required=True)
    client_parser.add_argument("--output", "-o", help="Output file (default: stdout)")

    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        # Execute command
        if args.command == "from-code":
            with open(args.input) as f:
                code = f.read()

            generator = OpenAPIGenerator()

            if args.framework == "fastapi":
                spec = generator.from_fastapi(code)
            elif args.framework == "flask":
                spec = generator.from_flask(code)
            elif args.framework == "express":
                spec = generator.from_express(code)

            output = json.dumps(spec, indent=2)

        elif args.command == "convert":
            with open(args.input) as f:
                swagger = json.load(f)

            generator = OpenAPIGenerator()
            spec = generator.convert_swagger_to_openapi(swagger)
            output = json.dumps(spec, indent=2)

        elif args.command == "generate-client":
            with open(args.input) as f:
                spec = json.load(f)

            output = generate_client_code(spec, args.language)

        # Write output
        if hasattr(args, "output") and args.output:
            with open(args.output, "w") as f:
                f.write(output)
            print(f"Generated: {args.output}")
        else:
            print(output)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
