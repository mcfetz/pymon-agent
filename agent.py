import argparse
import requests
import signal
import sys
import time
import os
import importlib.util

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

    plugins_dir = "plugins"
    if not os.path.exists(plugins_dir):
        os.makedirs(plugins_dir)

    previous_plugins = []
    while True:
        current_plugins = fetch_plugins()
        if current_plugins != previous_plugins:
            print("Plugins aktualisiert:", current_plugins)
            # Für jedes Plugin in der neuen Liste den Python-Code abrufen
            for plugin in current_plugins:
                plugin_url = f"{args.server}/plugin/{plugin}"
                headers = {"agentid": args.agentid}
                try:
                    response = requests.get(plugin_url, headers=headers)
                    response.raise_for_status()
                    plugin_code = response.text
                    # Speichere den Plugin-Code in der Datei plugins/{plugin}.py
                    plugin_file_path = os.path.join(plugins_dir, f"{plugin}.py")
                    with open(plugin_file_path, "w", encoding="utf-8") as f:
                        f.write(plugin_code)
                    print(f"Plugin '{plugin}' heruntergeladen und gespeichert.")
                except Exception as e:
                    print(f"Fehler beim Abrufen von Plugin '{plugin}': {e}")
            previous_plugins = current_plugins
        time.sleep(60)
