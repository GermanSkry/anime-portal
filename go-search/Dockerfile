# Build stage
FROM golang:1.21-alpine AS builder

WORKDIR /app

# Install dependencies
COPY go.mod go.sum ./
RUN go mod download

# Copy source code
COPY . .

# Build the application
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o search-service .

# Runtime stage
FROM alpine:3.18

WORKDIR /root/

# Copy binary from builder
COPY --from=builder /app/search-service .

# Expose port
EXPOSE 8001

# Run the service
CMD ["./search-service"]
