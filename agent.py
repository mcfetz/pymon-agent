import argparse
import requests
import signal
import sys
import time
import os
import importlib.util
from plugins.plugin_base import PluginBase

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
    current_plugins = []
    last_plugins_update = 0

    while True:
        current_time = time.time()
        # Aktualisiere die Plugin-Liste nur, wenn 60 Sekunden seit dem letzten Update vergangen sind
        if current_time - last_plugins_update >= 60:
            new_plugins = fetch_plugins()
            if new_plugins != previous_plugins:
                print("Plugins aktualisiert:", new_plugins)
                # Für jedes Plugin in der neuen Liste den Python-Code abrufen
                for plugin in new_plugins:
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
                previous_plugins = new_plugins
                current_plugins = new_plugins  # Update der global verwendeten Liste
            last_plugins_update = current_time

        # Metric-Erfassung für alle Plugins (außer "plugin_base")
        for plugin in current_plugins:
            if plugin == "plugin_base":
                continue
            plugin_file_path = os.path.join(plugins_dir, f"{plugin}.py")
            try:
                spec = importlib.util.spec_from_file_location(plugin, plugin_file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                # Suche nach der in diesem Modul definierten Klasse.
                plugin_classes = [
                    getattr(module, attr)
                    for attr in dir(module)
                    if isinstance(getattr(module, attr), type)
                    and not attr.startswith("__")
                ]
                if plugin_classes:
                    plugin_class = plugin_classes[0]
                    plugin_instance = plugin_class()
                    metric = plugin_instance.get_metric()
                    print(f"Metric von Plugin '{plugin}': {metric}")
                else:
                    print(f"Keine Klasse gefunden in Plugin '{plugin}'.")
            except Exception as e:
                print(f"Fehler beim Ausführen von Plugin '{plugin}': {e}")

        time.sleep(5)
