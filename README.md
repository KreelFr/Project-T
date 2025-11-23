Got it! Here’s the **full README in one clean block** without author info, ready to publish:

````markdown
# AutoTOR – Automatic TOR IP Rotator (WSL/Kali Linux)

AutoTOR is a Python-based TOR IP Rotator designed for **Kali Linux / WSL**.  
It automatically changes your TOR identity (new IP) at your chosen interval.  
Includes full installer + one‑command launcher.

---

## Features

- Automatically changes TOR IP address
- Custom rotation interval
- Clean terminal output
- Works inside WSL or Kali Linux
- One-command launcher (`ip`) for quick use
- Safe configuration using TOR HashedControlPassword

---

## Requirements

Make sure TOR is installed:

```bash
sudo apt update
sudo apt install tor -y
````

Enable and start TOR:

```bash
sudo service tor enable
sudo service tor start
```

---

## TOR Configuration

Update your TOR config:

```bash
sudo nano /etc/tor/torrc
```

Delete everything and paste this:

```bash
SocksPort 9050
ControlPort 9051

# Your authentication password hash (example)
HashedControlPassword 16:A5AC75C8166408B260899A7D37B54F995E8BAEE8CDDEAD3075C44754A0

DataDirectory /var/lib/tor
```

Save and restart TOR:

```bash
sudo service tor restart
sudo service tor status
```

---

## Python Environment Setup

Inside your project folder:

```bash
python3 -m venv venv
source venv/bin/activate
pip install stem pysocks requests
```

---

## Running Manually

Inside the project directory:

```bash
source venv/bin/activate
python3 autoTOR.py
```

---

## One‑Command Launcher (Recommended)

Create a launcher file:

```bash
sudo nano /usr/local/bin/ip
```

Paste:

```bash
#!/bin/bash
sudo service tor start
cd /home/kreelfr_/Project-T
source venv/bin/activate
python3 autoTOR.py
```

Make it executable:

```bash
sudo chmod +x /usr/local/bin/ip
```

Now you can run AutoTOR anywhere using:

```bash
ip
```

Or with sudo if needed:

```bash
sudo ip
```

---

## Example Output

```
[+] Starting AutoTOR...
[+] TOR is running.
[+] Current IP: 185.220.101.14
[+] New IP: 116.202.233.12
[+] New IP: 45.138.16.231
```

---

## Troubleshooting

**Connection refused**
TOR is not running. Fix:

```bash
sudo service tor start
```

**Authentication failed: no passphrase provided**
Your torrc password is missing or mismatched. Generate a new hash:

```bash
tor --hash-password yourpass
```

Replace the hash in `/etc/tor/torrc`, then restart TOR:

```bash
sudo service tor restart
```

**Missing dependencies for SOCKS support**
Install dependencies inside venv:

```bash
pip install pysocks requests[socks]
```

If using ZSH:

```bash
pip install "requests[socks]"
```
