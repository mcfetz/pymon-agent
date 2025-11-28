import argparse
import requests
import signal
import sys
import time
import os
import importlib.util
import threading
import queue
import logging
from plugins.plugin_base import PluginBase

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

metric_queue = queue.Queue()

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
        logging.error(f"Error sending status '{status}': {e}")


def fetch_plugins():
    url = f"{args.server}/plugins"
    headers = {"agentid": args.agentid}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        # Assumption: The endpoint returns a JSON array containing plugin names
        plugins = response.json()
        return plugins
    except Exception as e:
        logging.error(f"Error fetching plugins: {e}")
        return []


def signal_handler(sig, frame):
    logging.info("Shutting down agent... sending offline status.")
    send_status("offline")
    sys.exit(0)


def queue_metric(server_url: str, pluginid, metrics):
    """
    Adds the payload produced by get_metrics into the global metric queue.
    """
    headers = {"agentid": args.agentid}
    if isinstance(metrics, dict):
        metrics = [metrics]
    payload = {
        "pluginid": pluginid,
        "agentid": args.agentid,
        "metrics": metrics,
        "timestamp": time.time(),
        "headers": headers,
    }
    metric_queue.put((server_url, payload))


def run_plugin_instance(plugin, plugin_file_path):
    try:
        spec = importlib.util.spec_from_file_location(plugin, plugin_file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Search for the class defined in this module (excluding PluginBase)
        plugin_classes = [
            getattr(module, attr)
            for attr in dir(module)
            if isinstance(getattr(module, attr), type)
            and not attr.startswith("__")
            and "PluginBase" not in str(getattr(module, attr))
        ]
        if not plugin_classes:
            logging.error(f"No suitable class found in plugin '{plugin}'.")
            return
        plugin_class = plugin_classes[0]
        plugin_instance = plugin_class()
    except Exception as e:
        logging.error(f"Error loading plugin '{plugin}': {e}")
        return

    while True:
        try:
            metric = plugin_instance.get_metrics()
            logging.info(f"Plugin '{plugin}' metric: {metric}")
            queue_metric(
                server_url=args.server,
                pluginid=plugin_instance.get_plugin_id(),
                metrics=metric,
            )
        except Exception as e:
            logging.error(f"Error in get_metrics for plugin '{plugin}': {e}")
        try:
            sleep_time = plugin_instance.get_default_sleep()
        except Exception as e:
            logging.error(f"Error in get_default_sleep for plugin '{plugin}': {e}")
            sleep_time = 5  # Fallback-Schlafzeit
        time.sleep(sleep_time)


def download_plugins(plugins: list):
    for plugin in plugins:
        plugin_url = f"{args.server}/plugin/{plugin}"
        headers = {"agentid": args.agentid}
        try:
            response = requests.get(plugin_url, headers=headers)
            response.raise_for_status()
            plugin_code = response.text
            # Save the plugin code into the file plugins/{plugin}.py
            plugin_file_path = os.path.join(plugins_dir, f"{plugin}.py")
            with open(plugin_file_path, "w", encoding="utf-8") as f:
                f.write(plugin_code)
            logging.info(f"Plugin '{plugin}' successfully downloaded and stored.")
        except Exception as e:
            logging.error(f"Error while loading plugin '{plugin}': {e}")


def process_metric_queue():
    while True:
        logging.debug(f"Metric queue length: {metric_queue.qsize()}")
        try:
            server_url, payload = metric_queue.get()
            try:
                response = requests.post(
                    f"{server_url}/metric", json=payload, headers=payload["headers"]
                )
                # Wenn der POST-Request erfolgreich war (HTTP 2xx)
                if response.ok:
                    logging.debug(f"Metric sent, response status: {response.status_code}")
                    metric_queue.task_done()
                else:
                    logging.error(
                        f"Metric post unsuccessful (Status: {response.status_code}), requeuing"
                    )
                    # Requeue the metric for later retry.
                    metric_queue.put((server_url, payload))
                    metric_queue.task_done()
            except Exception as e:
                logging.error(f"Error sending metric: {e} - requeuing")
                metric_queue.put((server_url, payload))
                metric_queue.task_done()
        except Exception as e:
            logging.error(f"Error retrieving from queue: {e}")
        time.sleep(0.5)  # Kleine Pause, um die CPU-Last zu reduzieren


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


if __name__ == "__main__":
    plugins_dir = "plugins"
    if not os.path.exists(plugins_dir):
        os.makedirs(plugins_dir)

    plugin_threads = {}

    plugins = fetch_plugins()
    if len(plugins) == 0:
        logging.error("No plugins found. Exiting.")
        sys.exit(0)

    logging.info(f"Plugins assigned: {plugins}")
    download_plugins(plugins)

    send_status("online")
    logging.info("Agent online. Press Ctrl+C to quit.")

    # Starte den Thread zur Bearbeitung der Metric-Queue
    metric_thread = threading.Thread(target=process_metric_queue)
    metric_thread.daemon = True
    metric_thread.start()

    while True:
        for plugin in plugins:
            if plugin != "plugin_base" and plugin not in plugin_threads:
                plugin_file_path = os.path.join(plugins_dir, f"{plugin}.py")
                t = threading.Thread(
                    target=run_plugin_instance, args=(plugin, plugin_file_path)
                )
                t.daemon = True
                t.start()
                plugin_threads[plugin] = t

        time.sleep(5)
