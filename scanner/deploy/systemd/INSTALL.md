# Installing Scanner as a systemd Service

This guide explains how to install the momentum scanner as a systemd service on Ubuntu/Debian systems.

## Prerequisites

- Ubuntu 20.04+ or Debian 11+
- Python 3.10 or higher
- sudo access

## Installation Steps

### 1. Create Scanner User

```bash
sudo useradd -r -m -s /bin/bash scanner
```

### 2. Install Scanner

```bash
# Create installation directory
sudo mkdir -p /opt/scanner
sudo chown scanner:scanner /opt/scanner

# Copy scanner code
sudo cp -r /path/to/scanner /opt/scanner/
sudo chown -R scanner:scanner /opt/scanner

# Create virtual environment
sudo -u scanner python3 -m venv /opt/scanner/venv
sudo -u scanner /opt/scanner/venv/bin/pip install -r /opt/scanner/requirements.txt
```

### 3. Create Configuration Directory

```bash
sudo mkdir -p /etc/scanner /var/log/scanner /var/lib/scanner
sudo chown scanner:scanner /etc/scanner /var/log/scanner /var/lib/scanner

# Copy config
sudo cp /opt/scanner/scanner/config/config.example.json /etc/scanner/config.json
sudo chown scanner:scanner /etc/scanner/config.json

# Edit configuration
sudo nano /etc/scanner/config.json
```

### 4. Configure Environment Variables (Optional)

```bash
# Create .env file
sudo nano /etc/scanner/.env
```

Add your API keys:
```
FINNHUB_API_KEY=your_key_here
TWELVEDATA_API_KEY=your_key_here
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

```bash
sudo chown scanner:scanner /etc/scanner/.env
sudo chmod 600 /etc/scanner/.env
```

### 5. Install systemd Service Files

```bash
sudo cp /opt/scanner/scanner/deploy/systemd/scanner.service /etc/systemd/system/
sudo cp /opt/scanner/scanner/deploy/systemd/scanner.timer /etc/systemd/system/
```

### 6. Enable and Start Timer

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable timer to start on boot
sudo systemctl enable scanner.timer

# Start timer
sudo systemctl start scanner.timer

# Check status
sudo systemctl status scanner.timer
```

## Usage

### Check Timer Status

```bash
sudo systemctl status scanner.timer
sudo systemctl list-timers scanner.timer
```

### Run Scan Manually

```bash
sudo systemctl start scanner.service
```

### Check Service Logs

```bash
# View latest logs
sudo journalctl -u scanner.service -n 100 -f

# View logs from today
sudo journalctl -u scanner.service --since today

# View logs from specific date
sudo journalctl -u scanner.service --since "2024-01-01" --until "2024-01-02"
```

### Stop/Disable Scanner

```bash
# Stop timer
sudo systemctl stop scanner.timer

# Disable timer
sudo systemctl disable scanner.timer
```

## Customizing Schedule

To change the scan schedule, edit the timer file:

```bash
sudo nano /etc/systemd/system/scanner.timer
```

Change the `OnCalendar` line. Examples:
- `OnCalendar=*-*-* 07:00:00` - Daily at 7 AM
- `OnCalendar=Mon-Fri 09:00:00` - Weekdays at 9 AM
- `OnCalendar=*-*-* 09:00,15:00:00` - Daily at 9 AM and 3 PM

After editing:
```bash
sudo systemctl daemon-reload
sudo systemctl restart scanner.timer
```

## Troubleshooting

### Check Service Status
```bash
sudo systemctl status scanner.service
```

### View Detailed Logs
```bash
sudo journalctl -u scanner.service -xe
```

### Test Configuration
```bash
sudo -u scanner /opt/scanner/venv/bin/python -m scanner.modes.worker --config /etc/scanner/config.json
```

### Permissions Issues
```bash
sudo chown -R scanner:scanner /opt/scanner /etc/scanner /var/log/scanner /var/lib/scanner
```
