from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

class Handler(FileSystemEventHandler):
    def on_created(self, event):
        print(f"Neue Datei erkannt: {event.src_path}")
        # hier kommt später OCR + Klassifikation

def start_watcher(path):
    event_handler = Handler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)
    observer.start()

    print(f"Überwache: {path}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()