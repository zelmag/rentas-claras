# Deploying Rentas-Claras to Oracle Cloud (Free Forever)

## Overview
Oracle Cloud offers **Always Free** VMs that never expire - not a trial. You get:
- 2 AMD VMs (1GB RAM each) - forever free
- 50GB storage - forever free
- Full internet access for WhatsApp API

---

## Step 1: Create Oracle Cloud Account (5 min)

1. Go to: https://www.oracle.com/cloud/free/
2. Click **"Start for free"**
3. Fill in your details:
   - Use your real name (they verify identity)
   - Select **Home Region**: Choose one close to Mexico (e.g., "US West (Phoenix)" or "Brazil East (Sao Paulo)")
   - ⚠️ **Important**: Home region cannot be changed later!
4. Add a payment method (for verification only - you won't be charged)
5. Complete email verification and ID verification

---

## Step 2: Create a Free VM Instance (5 min)

1. Once logged in, go to: **Compute → Instances → Create Instance**

2. Configure the instance:
   - **Name**: `rentas-claras`
   - **Image**: Ubuntu 22.04 (or latest)
   - **Shape**: Click "Change Shape"
     - Select **"Ampere"** (ARM) → **VM.Standard.A1.Flex**
     - Set **1 OCPU** and **6 GB RAM** (this is free!)
     - OR select **AMD** → **VM.Standard.E2.1.Micro** (1GB RAM, also free)
   
3. **Networking**:
   - Create new VCN or use default
   - Assign public IP: **Yes**

4. **Add SSH Key**:
   - Select "Generate a key pair for me"
   - **Download both keys** (save them safely!)
   - OR paste your existing public key from: `~/.ssh/id_rsa.pub`

5. Click **Create** - wait 2-3 minutes for the instance to start

---

## Step 3: Open Firewall Ports (2 min)

1. Go to **Networking → Virtual Cloud Networks**
2. Click on your VCN → **Security Lists** → Default Security List
3. Click **Add Ingress Rules**:

   | Source CIDR | Protocol | Destination Port | Description |
   |-------------|----------|------------------|-------------|
   | 0.0.0.0/0   | TCP      | 5000             | Flask app   |
   | 0.0.0.0/0   | TCP      | 80               | HTTP        |
   | 0.0.0.0/0   | TCP      | 443              | HTTPS       |

---

## Step 4: Connect to Your VM (2 min)

Get your instance's **Public IP** from the Instances page, then:

```bash
# If you downloaded the key from Oracle:
chmod 600 ~/Downloads/ssh-key-*.key
ssh -i ~/Downloads/ssh-key-*.key ubuntu@YOUR_PUBLIC_IP

# If you used your existing key:
ssh ubuntu@YOUR_PUBLIC_IP
```

---

## Step 5: Install Dependencies (3 min)

Run these commands on the VM:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install -y python3 python3-pip python3-venv git

# Install SQLite (should be included, but just in case)
sudo apt install -y sqlite3

# Open firewall on Ubuntu (Oracle Cloud uses iptables)
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 5000 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo netfilter-persistent save
```

---

## Step 6: Deploy Rentas-Claras (5 min)

```bash
# Clone your repo
cd ~
git clone https://github.com/zelmag/vuelodigno.git
cd vuelodigno/rentas-claras

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with your settings
nano .env
```

Add to `.env`:
```
WHATSAPP_PHONE_ID=your_phone_id
WHATSAPP_TOKEN=your_token
# ... other env vars from .env.example
```

---

## Step 7: Run the App (Test)

```bash
# Test run
python app.py
```

Visit: `http://YOUR_PUBLIC_IP:5000`

---

## Step 8: Run Forever with Systemd (5 min)

Create a service file:

```bash
sudo nano /etc/systemd/system/rentas-claras.service
```

Paste this:

```ini
[Unit]
Description=Rentas Claras Flask App
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/vuelodigno/rentas-claras
Environment="PATH=/home/ubuntu/vuelodigno/rentas-claras/venv/bin"
EnvironmentFile=/home/ubuntu/vuelodigno/rentas-claras/.env
ExecStart=/home/ubuntu/vuelodigno/rentas-claras/venv/bin/gunicorn --bind 0.0.0.0:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable rentas-claras
sudo systemctl start rentas-claras

# Check status
sudo systemctl status rentas-claras
```

---

## Step 9: (Optional) Add Free Domain with Cloudflare

1. Get a free domain from https://freenom.com or use your own
2. Add to Cloudflare (free tier)
3. Point A record to your Oracle VM's public IP
4. Enable Cloudflare proxy for free SSL

---

## Updating the App

When you push changes to GitHub:

```bash
ssh ubuntu@YOUR_PUBLIC_IP
cd ~/vuelodigno/rentas-claras
git pull
sudo systemctl restart rentas-claras
```

---

## Troubleshooting

### Check logs:
```bash
sudo journalctl -u rentas-claras -f
```

### Restart app:
```bash
sudo systemctl restart rentas-claras
```

### Check if port is open:
```bash
sudo lsof -i :5000
```

---

## Cost Summary

| Resource | Cost |
|----------|------|
| VM (A1.Flex 1 OCPU, 6GB) | **$0 forever** |
| 50GB storage | **$0 forever** |
| Outbound data (10TB/month) | **$0 forever** |
| **Total** | **$0/month** |

This is Oracle's "Always Free" tier - not a trial, no expiration.
