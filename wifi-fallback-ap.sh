#!/bin/bash
# WiFi Fallback Access Point Script
# Attempts to connect to known WiFi networks, creates AP if connection fails

set -e

INTERFACE="wlP1p1s0"
AP_SSID="RosMower-AP"
AP_PASSWORD="rosmower123"
AP_IP="192.168.50.1"
CONNECTION_TIMEOUT=30

log() {
    echo "[WiFi-Fallback] $1" | tee -a /var/log/wifi-fallback.log
}

check_wifi_connection() {
    log "Checking for WiFi connection..."
    
    # Wait for network manager to attempt connection
    sleep $CONNECTION_TIMEOUT
    
    # Check if we have an IP address and internet connectivity
    if ip addr show $INTERFACE | grep -q "inet " && ping -c 1 -W 5 8.8.8.8 &>/dev/null; then
        log "WiFi connection successful"
        return 0
    else
        log "No WiFi connection detected"
        return 1
    fi
}

stop_network_manager() {
    log "Stopping NetworkManager..."
    systemctl stop NetworkManager 2>/dev/null || true
    systemctl stop wpa_supplicant 2>/dev/null || true
    sleep 2
}

start_network_manager() {
    log "Starting NetworkManager..."
    systemctl start NetworkManager 2>/dev/null || true
}

setup_access_point() {
    log "Setting up Access Point mode..."
    
    # Install required packages if not present
    if ! command -v hostapd &>/dev/null; then
        log "Installing hostapd..."
        apt-get update && apt-get install -y hostapd
    fi
    
    # Stop NetworkManager to configure manually
    stop_network_manager
    
    # Configure interface
    ip link set $INTERFACE down
    ip addr flush dev $INTERFACE
    ip addr add ${AP_IP}/24 dev $INTERFACE
    ip link set $INTERFACE up
    
    # Create hostapd config
    cat > /tmp/hostapd.conf <<EOF
interface=$INTERFACE
driver=nl80211
ssid=$AP_SSID
hw_mode=g
channel=6
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=$AP_PASSWORD
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF
    
    # Configure dnsmasq for DHCP
    cat > /tmp/dnsmasq-ap.conf <<EOF
interface=$INTERFACE
dhcp-range=192.168.50.10,192.168.50.50,255.255.255.0,24h
dhcp-option=3,$AP_IP
dhcp-option=6,$AP_IP
EOF
    
    # Stop any running instances
    killall hostapd 2>/dev/null || true
    killall dnsmasq 2>/dev/null || true
    
    # Start dnsmasq
    log "Starting DHCP server..."
    dnsmasq -C /tmp/dnsmasq-ap.conf --no-daemon &
    
    # Start hostapd
    log "Starting Access Point..."
    hostapd /tmp/hostapd.conf &
    
    log "Access Point active: SSID=$AP_SSID, Password=$AP_PASSWORD, IP=$AP_IP"
}

restore_wifi_mode() {
    log "Restoring WiFi client mode..."
    
    # Kill AP services
    killall hostapd 2>/dev/null || true
    killall dnsmasq 2>/dev/null || true
    
    # Reset interface
    ip link set $INTERFACE down
    ip addr flush dev $INTERFACE
    ip link set $INTERFACE up
    
    # Restart NetworkManager
    start_network_manager
    
    log "WiFi client mode restored"
}

main() {
    log "WiFi Fallback AP starting..."
    
    # Check if interface exists
    if ! ip link show $INTERFACE &>/dev/null; then
        log "ERROR: Interface $INTERFACE not found"
        exit 1
    fi
    
    # Try to connect to WiFi
    start_network_manager
    
    if ! check_wifi_connection; then
        log "Failed to connect to WiFi, switching to AP mode..."
        setup_access_point
        
        # Keep script running and periodically check if WiFi becomes available
        while true; do
            sleep 300  # Check every 5 minutes
            log "Checking if WiFi network is available..."
            restore_wifi_mode
            
            if check_wifi_connection; then
                log "WiFi connection established, staying in client mode"
                break
            else
                log "Still no WiFi, reverting to AP mode..."
                setup_access_point
            fi
        done
    else
        log "WiFi connected, staying in client mode"
    fi
}

# Handle script termination
trap restore_wifi_mode EXIT INT TERM

main
