#!/bin/bash
# Quick launcher for RTKLIB with NTRIP base corrections
# Server: 10.0.213.211
# Mount Point: BASE
# Username: nfazio

RTKLIB_BIN="/mnt/nova_ssd/rosmowercompleate/src/gps_rtk/rtklib/rtkrcv"
NTRIP_CONFIG="/mnt/nova_ssd/rosmowercompleate/src/gps_rtk/config/ntrip_rover.conf"

echo "🚀 Launching RTKLIB with NTRIP corrections..."
echo "   Server: 10.0.213.211"
echo "   Mount: BASE"
echo "   Baud: 115200"
echo "   Output: TCP :9001 (NMEA)"
echo ""

# Start with -s flag to auto-start RTK server
# Use -t 2 for debug level 2 (optional)
"$RTKLIB_BIN" -o "$NTRIP_CONFIG" -s -t 2
