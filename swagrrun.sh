#!/bin/bash

# High-Assurance API: Swagger UI Controller
CONTAINER_NAME="hsa-swagger-ui"

case "$1" in
    -c|--cleanup|stop)
        echo "🛑 Stopping Swagger UI..."
        docker stop $CONTAINER_NAME > /dev/null 2>&1
        echo "✅ Cleanup complete. Port 8080 is now free."
        ;;
    *)
        # Default behavior: Start the UI
        # First, ensure any old instance is killed to avoid port conflicts
        docker stop $CONTAINER_NAME > /dev/null 2>&1
        
        echo "🚀 Starting Swagger UI in the background..."
        docker run -d --rm \
          --name $CONTAINER_NAME \
          -p 8081:8080 \
          -e SWAGGER_JSON=/app/openapi.yaml \
          -v "$(pwd):/app" \
          swaggerapi/swagger-ui > /dev/null
        
        echo "✅ Swagger UI is live at http://localhost:8080"
        echo "💡 To stop it later, run: swagrrun -c"
        ;;
esac
