#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_changer.py
All-in-one: TOR (NEWNYM), Proxy rotation, OpenVPN rotation.
Safe defaults: asks for confirmation before privileged actions.
Requires: Python 3.8+, requests (for IP checks).
Author: safe rewrite (based on user's original)
"""

import os
import sys
import time
import signal
import subprocess
import argparse
import threading
from datetime import datetime

try:
    import requests
except Exception as e:
    print("The 'requests' package is required. Install with: pip3 install requests")
    sys.exit(1)

LOGFILE = os.path.expanduser("~/.auto_changer.log")

def log(msg):
    s = f"{datetime.utcnow().isoformat()} UTC | {msg}"
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(s + "\n")
    print(msg)

def check_ip(proxies=None, timeout=10):
    """Return the current external IP (string) using checkip.amazonaws.com"""
    url = "http://checkip.amazonaws.com"
    try:
        r = requests.get(url, proxies=proxies, timeout=timeout)
        ip = r.text.strip()
        return ip
    except Exception as e:
        return f"ERROR: {e}"

# ---------------- TOR ----------------
def tor_newnym_via_control(control_host="127.0.0.1", control_port=9051, password=None, timeout=5):
    """
    Attempt to send NEWNYM via Tor ControlPort.
    Returns True on success, False otherwise.
    Requires Tor to be configured with ControlPort and either CookieAuth or a password.
    """
    import socket
    try:
        s = socket.create_connection((control_host, control_port), timeout=timeout)
        s_file = s.makefile(mode="rw")
        if password:
            s_file.write(f'AUTHENTICATE "{password}"\r\n')
        else:
            s_file.write("AUTHENTICATE\r\n")
        s_file.flush()
        auth_resp = s_file.readline()
        if not auth_resp.startswith("250"):
            log(f"Tor control auth failed: {auth_resp.strip()}")
            s.close()
            return False
        s_file.write("SIGNAL NEWNYM\r\n")
        s_file.flush()
        resp = s_file.readline()
        s.close()
        if resp.startswith("250"):
            return True
        else:
            log(f"Tor control SIGNAL response: {resp.strip()}")
            return False
    except Exception as e:
        log(f"Tor control error: {e}")
        return False

def tor_reload_service():
    """Ask for confirmation then restart/reload tor service (requires sudo)."""
    log("Attempting to restart 'tor' service (requires sudo).")
    ans = input("This will run 'sudo systemctl restart tor' (or 'service tor restart'). Continue? [y/N] >> ").strip().lower()
    if ans != "y":
        log("User declined to restart tor service.")
        return False
    cmd_try = [["systemctl", "restart", "tor"], ["service", "tor", "restart"]]
    for cmd in cmd_try:
        try:
            subprocess.check_call(["sudo"] + cmd)
            log(f"Ran: sudo {' '.join(cmd)}")
            return True
        except subprocess.CalledProcessError:
            continue
        except FileNotFoundError:
            continue
    log("Could not restart tor service automatically. Please restart tor manually.")
    return False

def tor_change_identity(control_password=None):
    ok = tor_newnym_via_control(password=control_password)
    if ok:
        log("Requested NEWNYM via Tor control port.")
        return True
    else:
        log("Tor control port NEWNYM failed; falling back to service restart.")
        return tor_reload_service()

# ---------------- Proxy rotation ----------------
def load_proxy_list(path):
    """Load proxy list from a file. Each line: protocol://host:port (or socks5h://...)."""
    proxies = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            proxies.append(s)
    return proxies

def proxy_to_requests_proxies(proxy_url):
    """Map a single proxy url to requests' proxies dict for both http and https."""
    return {"http": proxy_url, "https": proxy_url}

# ---------------- VPN rotation ----------------
def find_ovpn_files(dirpath):
    return [os.path.join(dirpath, p) for p in sorted(os.listdir(dirpath)) if p.lower().endswith(".ovpn")]

def start_openvpn(config_path):
    """Start an openvpn process in the foreground. Returns subprocess.Popen or None.
    This command likely requires sudo. We run via 'sudo openvpn --config <file>'"""
    log(f"Starting OpenVPN config: {config_path}")
    try:
        p = subprocess.Popen(["sudo", "openvpn", "--config", config_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        time.sleep(2)  # give it a moment
        if p.poll() is None:
            log("OpenVPN process started.")
            return p
        else:
            log(f"OpenVPN process exited quickly. Returncode: {p.returncode}")
            return None
    except FileNotFoundError:
        log("openvpn binary not found. Install OpenVPN (e.g. apt install openvpn).")
        return None
    except Exception as e:
        log(f"Failed to start openvpn: {e}")
        return None

def stop_process(p):
    try:
        p.terminate()
        p.wait(timeout=10)
        log("VPN process terminated.")
    except Exception:
        try:
            p.kill()
        except Exception:
            pass
        log("VPN process killed.")

# ---------------- Orchestration ----------------
class AutoChanger:
    def __init__(self, args):
        self.args = args
        self.stop_event = threading.Event()
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        log("Interrupt received, stopping...")
        self.stop_event.set()

    def run_once_tor(self):
        before = check_ip()
        log(f"IP before (direct): {before}")
        ok = tor_change_identity(control_password=self.args.tor_control_password)
        if not ok:
            log("TOR identity change did not complete.")
            return
        # wait a bit and check IP through tor proxy
        time.sleep(self.args.wait_after_change)
        try:
            tor_proxies = {"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}
            after = check_ip(proxies=tor_proxies)
            log(f"IP after (via TOR): {after}")
        except Exception as e:
            log(f"Failed to check IP via tor: {e}")

    def run_once_proxy(self, proxy_url):
        before = check_ip()
        log(f"IP before (direct): {before}")
        proxies = proxy_to_requests_proxies(proxy_url)
        time.sleep(self.args.wait_after_change)
        after = check_ip(proxies=proxies)
        log(f"IP via proxy {proxy_url}: {after}")

    def run_once_vpn(self, ovpn_path):
        before = check_ip()
        log(f"IP before (direct): {before}")
        p = start_openvpn(ovpn_path)
        if not p:
            log("OpenVPN failed to start for this config.")
            return
        # give VPN time to establish
        wait = max(5, self.args.wait_after_change)
        log(f"Sleeping {wait} seconds for VPN to establish...")
        time.sleep(wait)
        after = check_ip()
        log(f"IP after VPN: {after}")
        # stop vpn
        stop_process(p)
        time.sleep(2)

    def run_loop(self):
        # prepare lists
        proxies = []
        if self.args.proxy_list:
            proxies = load_proxy_list(self.args.proxy_list)
            log(f"Loaded {len(proxies)} proxies from {self.args.proxy_list}")

        ovpns = []
        if self.args.ovpn_dir:
            ovpns = find_ovpn_files(self.args.ovpn_dir)
            log(f"Found {len(ovpns)} .ovpn files in {self.args.ovpn_dir}")

        iteration = 0
        while not self.stop_event.is_set():
            iteration += 1
            log(f"--- Iteration {iteration} ---")
            # TOR mode
            if self.args.mode in ("tor", "all"):
                log("Running TOR change...")
                self.run_once_tor()

            # Proxy mode
            if self.args.mode in ("proxy", "all") and proxies:
                for purl in proxies:
                    if self.stop_event.is_set(): break
                    log(f"Using proxy: {purl}")
                    self.run_once_proxy(purl)
                    self._wait_or_stop()

            # VPN mode
            if self.args.mode in ("vpn", "all") and ovpns:
                for cfg in ovpns:
                    if self.stop_event.is_set(): break
                    log(f"Using VPN config: {cfg}")
                    self.run_once_vpn(cfg)
                    self._wait_or_stop()

            if self.args.mode == "proxy" and not proxies:
                log("No proxies provided; sleeping.")
                self._wait_or_stop()
            if self.args.mode == "vpn" and not ovpns:
                log("No .ovpn files provided; sleeping.")
                self._wait_or_stop()

            # if mode is single-run, break
            if self.args.run_once:
                log("run_once specified; exiting loop.")
                break

            # if user asked for a limited count
            if self.args.count and iteration >= self.args.count:
                log(f"Reached count {self.args.count}, exiting.")
                break

        log("AutoChanger finished.")

    def _wait_or_stop(self):
        total = self.args.interval
        start = time.time()
        while time.time() - start < total:
            if self.stop_event.is_set():
                break
            time.sleep(0.5)

# ---------------- CLI ----------------
def parse_args():
    p = argparse.ArgumentParser(description="Auto IP changer (TOR / proxy / VPN). Be careful with sudo-required actions.")
    p.add_argument("--mode", choices=["tor", "proxy", "vpn", "all"], default="tor", help="Mode to run")
    p.add_argument("--interval", type=int, default=60, help="Seconds between changes (routing duration).")
    p.add_argument("--wait-after-change", type=int, default=5, help="Seconds to wait after change before checking IP.")
    p.add_argument("--proxy-list", type=str, help="Path to newline-separated proxy list (protocol://host:port).")
    p.add_argument("--ovpn-dir", type=str, help="Directory containing .ovpn files to rotate through.")
    p.add_argument("--tor-control-password", type=str, help="Tor ControlPort password (if configured).")
    p.add_argument("--count", type=int, default=0, help="Number of iterations (0 = infinite).")
    p.add_argument("--run-once", action="store_true", help="Perform one cycle and exit.")
    p.add_argument("--dry-run", action="store_true", help="Do not perform privileged actions; just show what would happen.")
    p.add_argument("--logfile", type=str, default=LOGFILE, help="Log file path.")
    return p.parse_args()

def main():
    args = parse_args()
    global LOGFILE
    LOGFILE = args.logfile

    log("AutoChanger started. Mode: " + args.mode)
    if args.dry_run:
        log("Dry-run mode enabled. Privileged actions will NOT run.")
    changer = AutoChanger(args)
    try:
        changer.run_loop()
    except Exception as e:
        log(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    main()
