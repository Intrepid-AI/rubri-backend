#!/bin/bash
# Simple startup script for Docker container
echo "Starting Rubri Backend Services..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf