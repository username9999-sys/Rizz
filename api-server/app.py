#!/usr/bin/env python3
"""
Rizz API Server - Main Entry Point
Enterprise-grade Flask application
"""

import os
from pathlib import Path

# Import the application factory
from app import create_app

# Determine configuration
config_name = os.environ.get('FLASK_ENV', 'development')

# Create application
app = create_app(config_name)

if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    print("\n" + "=" * 60)
    print("🚀 Rizz API Server v2.0 - Enterprise Edition")
    print("=" * 60)
    print(f"Environment: {config_name}")
    print(f"Server: http://{host}:{port}")
    print(f"API Docs: http://{host}:{port}/api")
    print(f"Health Check: http://{host}:{port}/health")
    print(f"Metrics: http://{host}:{port}/metrics")
    print("=" * 60)
    print("\nDefault Admin Credentials:")
    print("  Username: admin")
    print("  Password: admin123")
    print("\n⚠️  Change these credentials in production!\n")
    
    app.run(host=host, port=port, debug=debug)
