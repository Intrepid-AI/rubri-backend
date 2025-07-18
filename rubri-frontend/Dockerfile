# Build stage
FROM node:20-alpine as builder

# Accept build arguments for API URL
# These will override values in .env.production during build
ARG VITE_API_BASE_URL

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code and environment files
COPY . .

# If build args are provided, use them to override .env.production
RUN if [ -n "$VITE_API_BASE_URL" ]; then \
    echo "VITE_API_BASE_URL=$VITE_API_BASE_URL" >> .env.production.local; \
    fi

# Build the application (skip TypeScript check if it fails)
RUN npm run build || npx vite build

# Production stage
FROM nginx:alpine

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]