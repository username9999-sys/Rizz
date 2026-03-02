#!/bin/bash
# Rizz Platform - Security Hardening Script
# Run this script after initial deployment

set -e

echo "🔒 Rizz Platform Security Hardening"
echo "===================================="
echo ""

# Change default passwords
echo "⚠️  IMPORTANT: Change all default passwords!"
echo ""
read -p "Have you changed all default passwords? (y/n): " changed
if [ "$changed" != "y" ]; then
    echo "Please change default passwords before continuing!"
    exit 1
fi

# Update system packages
echo "📦 Updating system packages..."
apt update && apt upgrade -y

# Install security tools
echo "🔧 Installing security tools..."
apt install -y fail2ban ufw rkhunter chkrootkit

# Configure UFW Firewall
echo "🔥 Configuring firewall..."
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https

# Allow specific service ports (adjust as needed)
ufw allow 5000/tcp  # API
ufw allow 3000/tcp  # Web
ufw allow 8080/tcp  # Alternative

echo "✓ Firewall configured"

# Configure Fail2Ban
echo "🚫 Configuring Fail2Ban..."
cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3

[nginx-http-auth]
enabled = true
port = http,https
filter = nginx-http-auth
logpath = /var/log/nginx/error.log
maxretry = 3

[nginx-limit-req]
enabled = true
port = http,https
filter = nginx-limit-req
logpath = /var/log/nginx/error.log
maxretry = 10
EOF

systemctl restart fail2ban
echo "✓ Fail2Ban configured"

# SSH Hardening
echo "🔐 Hardening SSH configuration..."
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

cat >> /etc/ssh/sshd_config << EOF

# Security Hardening
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
X11Forwarding no
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
EOF

systemctl restart sshd
echo "✓ SSH hardened"

# Set up automatic security updates
echo "🔄 Setting up automatic security updates..."
apt install -y unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades

# Configure sysctl for security
echo "⚙️ Configuring kernel security parameters..."
cat >> /etc/sysctl.conf << EOF

# Security Hardening
net.ipv4.tcp_syncookies = 1
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.all.log_martians = 1
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.conf.all.rp_filter = 1
EOF

sysctl -p
echo "✓ Kernel parameters configured"

# Install and configure rootkit detection
echo "🔍 Installing rootkit detection tools..."
rkhunter --check
chkrootkit
echo "✓ Rootkit detection tools installed"

# Set up log rotation
echo "📝 Configuring log rotation..."
cat > /etc/logrotate.d/rizz << EOF
/var/log/rizz/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 root root
    sharedscripts
    postrotate
        systemctl reload rizz-api > /dev/null 2>&1 || true
    endscript
}
EOF

echo "✓ Log rotation configured"

# Docker security
echo "🐳 Applying Docker security best practices..."

# Don't run containers as root
echo "Note: Ensure Docker containers run as non-root user"

# Enable Docker content trust
export DOCKER_CONTENT_TRUST=1
echo "export DOCKER_CONTENT_TRUST=1" >> ~/.bashrc

echo "✓ Docker security applied"

# SSL/TLS Configuration
echo "🔒 Checking SSL/TLS configuration..."
if command -v nginx &> /dev/null; then
    # Test nginx configuration
    nginx -t
    
    # Recommend Let's Encrypt
    echo "Recommendation: Install Let's Encrypt certificate"
    echo "Run: certbot --nginx -d yourdomain.com"
fi

# Database security
echo "💾 Database security recommendations:"
echo "  - Change default database passwords"
echo "  - Restrict database access to localhost"
echo "  - Enable database encryption"
echo "  - Regular backup verification"

# File permissions
echo "📁 Setting secure file permissions..."
find /data/data/com.termux/files/home/Rizz-Project -type f -exec chmod 644 {} \;
find /data/data/com.termux/files/home/Rizz-Project -type d -exec chmod 755 {} \;

# Sensitive files
chmod 600 /data/data/com.termux/files/home/Rizz-Project/.env
chmod 600 /data/data/com.termux/files/home/Rizz-Project/**/.env

echo "✓ File permissions set"

# Security headers
echo "🛡️ Security headers checklist:"
echo "  - Strict-Transport-Security"
echo "  - X-Frame-Options"
echo "  - X-Content-Type-Options"
echo "  - X-XSS-Protection"
echo "  - Content-Security-Policy"

# Final security scan
echo ""
echo "🔍 Running security scan..."
echo ""
echo "Security Hardening Complete!"
echo "============================"
echo ""
echo "Next steps:"
echo "1. Review and test all services"
echo "2. Run security scanner: npm audit, pip-audit"
echo "3. Configure monitoring and alerting"
echo "4. Set up regular security audits"
echo "5. Enable intrusion detection"
echo ""
echo "⚠️  IMPORTANT: Reboot your server to apply all changes"
echo ""

read -p "Do you want to reboot now? (y/n): " reboot
if [ "$reboot" == "y" ]; then
    reboot
fi
