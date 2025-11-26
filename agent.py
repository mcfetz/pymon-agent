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

def fetch_plugins():
    url = f"{args.server}/plugins"
    headers = {"agentid": args.agentid}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        # Annahme: Der Endpunkt liefert ein JSON-Array mit den Plugin-Namen
        plugins = response.json()
        return plugins
    except Exception as e:
        print(f"Fehler beim Abrufen der Plugins: {e}")
        return []

def signal_handler(sig, frame):
    print("Beende Agent... sende offline Status.")
    send_status("offline")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    send_status("online")
    print("Agent online. Drücke Strg+C zum Beenden.")
    previous_plugins = []
    while True:
        time.sleep(60)
        current_plugins = fetch_plugins()
        if current_plugins != previous_plugins:
            print("Plugins aktualisiert:", current_plugins)
            previous_plugins = current_plugins
