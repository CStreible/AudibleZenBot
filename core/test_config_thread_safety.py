import threading
import time
from core.config import ConfigManager
from core.logger import get_logger

logger = get_logger(__name__)

# Test function for writing config in a thread
def write_config(manager, key, value, delay=0):
    time.sleep(delay)
    manager.set(key, value)
    logger.info(f"[Writer] Set {key} = {value}")

# Test function for reading config in a thread
def read_config(manager, key, delay=0):
    time.sleep(delay)
    value = manager.get(key)
    logger.info(f"[Reader] Got {key} = {value}")

def main():
    manager = ConfigManager()
    threads = []
    # Start several writers and readers
    for i in range(5):
        t = threading.Thread(target=write_config, args=(manager, f"test.key{i}", f"value{i}", i*0.1))
        threads.append(t)
        t.start()
    for i in range(5):
        t = threading.Thread(target=read_config, args=(manager, f"test.key{i}", i*0.15))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    logger.info("[Test] All threads finished.")

if __name__ == "__main__":
    main()
