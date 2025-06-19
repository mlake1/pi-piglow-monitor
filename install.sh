#!/bin/bash

# Pi-hole PiGlow Monitor - Automated Installer
# This script sets up the Pi-hole PiGlow monitor with all dependencies

set -e  # Exit on any error

INSTALL_DIR="/opt/pihole-piglow"
SERVICE_NAME="pihole-piglow"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Check if Pi-hole is installed and running
check_pihole() {
    print_status "Checking Pi-hole installation..."
    
    if command -v pihole >/dev/null 2>&1; then
        print_success "Pi-hole found"
        
        # Test API
        if curl -s http://localhost/admin/api.php >/dev/null 2>&1; then
            print_success "Pi-hole API accessible"
        else
            print_warning "Pi-hole API not accessible - monitor may not work correctly"
        fi
    else
        print_error "Pi-hole not found. Please install Pi-hole first:"
        print_error "curl -sSL https://install.pi-hole.net | bash"
        exit 1
    fi
}

# Update system packages
update_system() {
    print_status "Updating system packages..."
    apt update && apt upgrade -y
    print_success "System updated"
}

# Install required packages
install_dependencies() {
    print_status "Installing dependencies..."
    
    # Install system packages
    apt install -y python3-pip python3-dev i2c-tools
    
    # Install Python packages
    pip3 install piglow requests psutil
    
    print_success "Dependencies installed"
}

# Enable I2C interface
enable_i2c() {
    print_status "Enabling I2C interface..."
    
    # Enable I2C in config.txt
    if ! grep -q "dtparam=i2c_arm=on" /boot/config.txt; then
        echo "dtparam=i2c_arm=on" >> /boot/config.txt
        print_success "I2C enabled in /boot/config.txt"
    else
        print_success "I2C already enabled"
    fi
    
    # Load I2C modules
    modprobe i2c-dev
    modprobe i2c-bcm2708
    
    # Add to modules
    if ! grep -q "i2c-dev" /etc/modules; then
        echo "i2c-dev" >> /etc/modules
    fi
}

# Test PiGlow hardware
test_piglow() {
    print_status "Testing PiGlow hardware..."
    
    # Check if I2C device is detected
    if i2cdetect -y 1 | grep -q "54"; then
        print_success "PiGlow detected on I2C bus"
    else
        print_warning "PiGlow not detected. Please check connections."
        print_warning "Installation will continue, but hardware test may fail."
    fi
}

# Create installation directory
create_directories() {
    print_status "Creating installation directories..."
    
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$INSTALL_DIR/logs"
    
    print_success "Directories created"
}

# Install monitor files
install_files() {
    print_status "Installing monitor files..."
    
    # Copy main script
    cp pihole_monitor.py "$INSTALL_DIR/"
    chmod +x "$INSTALL_DIR/pihole_monitor.py"
    
    # Copy or create config file
    if [[ -f "config.json" ]]; then
        cp config.json "$INSTALL_DIR/"
    else
        # Create default config
        cat > "$INSTALL_DIR/config.json" << EOF
{
    "pihole_api_url": "http://localhost/admin/api.php",
    "update_interval": 10,
    "temperature_warning": 60,
    "temperature_critical": 70,
    "cpu_warning": 80,
    "memory_warning": 85,
    "brightness_scale": 1.0,
    "enable_startup_animation": true
}
EOF
    fi
    
    # Copy examples if they exist
    if [[ -d "examples" ]]; then
        cp -r examples "$INSTALL_DIR/"
    fi
    
    # Set ownership
    chown -R pi:pi "$INSTALL_DIR"
    
    print_success "Files installed to $INSTALL_DIR"
}

# Install systemd service
install_service() {
    print_status "Installing systemd service..."
    
    # Create service file
    cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=Pi-hole PiGlow Monitor
Documentation=https://github.com/mlake1/pihole-piglow-monitor
After=network.target pihole-FTL.service
Wants=pihole-FTL.service

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/pihole_monitor.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Environment
Environment=PYTHONUNBUFFERED=1

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$INSTALL_DIR

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable "${SERVICE_NAME}.service"
    
    print_success "Service installed and enabled"
}

# Test installation
test_installation() {
    print_status "Testing installation..."
    
    # Test script execution
    if sudo -u pi python3 "$INSTALL_DIR/pihole_monitor.py" test; then
        print_success "Monitor test passed"
    else
        print_error "Monitor test failed"
        return 1
    fi
}

# Create uninstall script
create_uninstaller() {
    print_status "Creating uninstaller..."
    
    cat > "$INSTALL_DIR/uninstall.sh" << 'EOF'
#!/bin/bash

# Pi-hole PiGlow Monitor Uninstaller

SERVICE_NAME="pihole-piglow"
INSTALL_DIR="/opt/pihole-piglow"

echo "Uninstalling Pi-hole PiGlow Monitor..."

# Stop and disable service
systemctl stop "$SERVICE_NAME" 2>/dev/null || true
systemctl disable "$SERVICE_NAME" 2>/dev/null || true

# Remove service file
rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
systemctl daemon-reload

# Remove installation directory
rm -rf "$INSTALL_DIR"

# Remove Python packages (optional - commented out to avoid affecting other projects)
# pip3 uninstall -y piglow requests psutil

echo "Pi-hole PiGlow Monitor uninstalled successfully"
echo "Note: I2C interface was left enabled"
echo "Note: Python packages were left installed"
EOF
    
    chmod +x "$INSTALL_DIR/uninstall.sh"
    print_success "Uninstaller created at $INSTALL_DIR/uninstall.sh"
}

# Main installation function
main() {
    echo
    echo "=========================================="
    echo "Pi-hole PiGlow Monitor Installer"
    echo "=========================================="
    echo
    
    check_root
    check_pihole
    update_system
    install_dependencies
    enable_i2c
    test_piglow
    create_directories
    install_files
    install_service
    create_uninstaller
    
    echo
    print_success "Installation completed successfully!"
    echo
    print_status "Next steps:"
    echo "  1. Reboot your Raspberry Pi to ensure I2C is fully enabled:"
    echo "     sudo reboot"
    echo
    echo "  2. After reboot, start the monitor:"
    echo "     sudo systemctl start $SERVICE_NAME"
    echo
    echo "  3. Check the status:"
    echo "     sudo systemctl status $SERVICE_NAME"
    echo
    echo "  4. View logs:"
    echo "     sudo journalctl -u $SERVICE_NAME -f"
    echo
    echo "Configuration file: $INSTALL_DIR/config.json"
    echo "Uninstaller: $INSTALL_DIR/uninstall.sh"
    echo
    
    # Ask if user wants to reboot now
    read -p "Would you like to reboot now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Rebooting in 5 seconds..."
        sleep 5
        reboot
    else
        print_warning "Please reboot manually before starting the service"
    fi
}

# Run main function
main "$@"
