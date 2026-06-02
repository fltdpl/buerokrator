from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from src.core.logger import logger
from src.processor.document_processor import process

import time


class Handler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return

        print(f"Neue Datei erkannt: {event.src_path}")
        logger.info(f"Neue Datei erkannt: {event.src_path}")
        process(event.src_path)



def start_watcher(path):
    event_handler = Handler()
    observer = Observer()
    observer.schedule(
        event_handler,
        path,
        recursive=False
    )

    observer.start()
    logger.info(f"Watcher gestartet für: {path}")
    print(f"Überwache: {path}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Watcher beendet")
        observer.stop()

    observer.join()