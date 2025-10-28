# Container Lambda example using official AWS base images
#
# Supports up to 10GB image size
# Works with existing Lambda features (layers, environment variables, etc.)

# Use AWS Lambda Python base image
FROM public.ecr.aws/lambda/python:3.12

# Install system dependencies if needed
RUN yum install -y \
    gcc \
    python3-devel \
    && yum clean all

# Copy requirements and install dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Copy function code
COPY python/api_lambda.py ${LAMBDA_TASK_ROOT}/

# Set the CMD to your handler
CMD ["api_lambda.lambda_handler"]

# Alternative: For custom runtime or entry point
# ENTRYPOINT ["/lambda-entrypoint.sh"]
# CMD ["custom_handler.handler"]

# Multi-stage build example for smaller images
# FROM public.ecr.aws/lambda/python:3.12 as builder
#
# # Build dependencies
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt -t /asset
#
# FROM public.ecr.aws/lambda/python:3.12
#
# # Copy only what's needed
# COPY --from=builder /asset ${LAMBDA_TASK_ROOT}
# COPY python/api_lambda.py ${LAMBDA_TASK_ROOT}/
#
# CMD ["api_lambda.lambda_handler"]

# Node.js example
# FROM public.ecr.aws/lambda/nodejs:20
#
# COPY package*.json ${LAMBDA_TASK_ROOT}/
# RUN npm ci --production
#
# COPY node/*.js ${LAMBDA_TASK_ROOT}/
#
# CMD ["dynamodb_trigger.handler"]

# Go example (using provided runtime)
# FROM public.ecr.aws/lambda/provided:al2
#
# COPY bootstrap ${LAMBDA_RUNTIME_DIR}/
# COPY main ${LAMBDA_TASK_ROOT}/
#
# CMD ["main"]

# Testing locally with Docker
#
# Build:
#   docker build -t my-lambda-function .
#
# Run:
#   docker run -p 9000:8080 my-lambda-function
#
# Test:
#   curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" \
#     -d '{"httpMethod": "GET", "path": "/items"}'
#
# With environment variables:
#   docker run -p 9000:8080 \
#     -e TABLE_NAME=my-table \
#     -e LOG_LEVEL=DEBUG \
#     my-lambda-function
#
# Deploy:
#   # Authenticate to ECR
#   aws ecr get-login-password --region us-east-1 | \
#     docker login --username AWS --password-stdin \
#     123456789012.dkr.ecr.us-east-1.amazonaws.com
#
#   # Tag
#   docker tag my-lambda-function:latest \
#     123456789012.dkr.ecr.us-east-1.amazonaws.com/my-lambda-function:latest
#
#   # Push
#   docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-lambda-function:latest
#
#   # Create/update function
#   aws lambda update-function-code \
#     --function-name my-function \
#     --image-uri 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-lambda-function:latest
