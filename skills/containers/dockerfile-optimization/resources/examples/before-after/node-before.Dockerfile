# BEFORE OPTIMIZATION
# Issues: Full base image, installs dev dependencies, no layer optimization

FROM node:20
WORKDIR /app

# Copies everything first (cache invalidation)
COPY . .

# Installs all dependencies including dev
RUN npm install

# Runs as root
# No health check
CMD npm start

# Result: ~1.1GB image, includes dev dependencies and build tools
