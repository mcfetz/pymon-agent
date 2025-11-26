import argparse
import requests
import signal
import sys
import time

parser = argparse.ArgumentParser(description="Monitoring Agent")
parser.add_argument("--server", required=True, help="Server URL")
parser.add_argument("--agentid", required=True, help="Agent ID")
args = parser.parse_args()

def send_status(status):
    url = f"{args.server}/status"
    params = {status: ""}
    headers = {"agentid": args.agentid}
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"Fehler beim Senden des Status '{status}': {e}")

def signal_handler(sig, frame):
    print("Beende Agent... sende offline Status.")
    send_status("offline")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    send_status("online")
    print("Agent online. Drücke Strg+C zum Beenden.")
    while True:
        time.sleep(1)
