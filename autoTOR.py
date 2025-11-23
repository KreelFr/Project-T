#!/usr/bin/env python3

import time
from stem import Signal
from stem.control import Controller

def change_ip():
    try:
        with Controller.from_port(port=9051) as controller:
            controller.authenticate()   # If you set a password, pass it: authenticate(password="yourpass")
            controller.signal(Signal.NEWNYM)
            print("[+] Requested new TOR identity (New IP)")
    except Exception as e:
        print("[!] Error while changing IP:", e)

def main():
    print("=== Auto TOR IP Changer (WSL/Kali Safe) ===")
    
    try:
        interval = int(input("Rotate IP every how many seconds? >> "))
    except:
        interval = 30
        print("[!] Invalid input. Using default: 30 seconds")

    print("\n[+] Starting rotation... Press CTRL+C to stop.\n")

    while True:
        change_ip()
        for n in range(interval):
            print(f"[*] Next IP change in {interval-n} seconds...", end="\r")
            time.sleep(1)

if __name__ == "__main__":
    main()
