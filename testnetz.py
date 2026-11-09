import subprocess
import time
import re
import statistics
from collections import deque

TARGET = "poolpumpe"
INTERVAL = 1.0
WINDOW = 30

latencies = deque(maxlen=WINDOW)

def ping_once(target):
    try:
        result = subprocess.run(
            ["ping", "-n", "1", target],
            capture_output=True,
            text=True,
            encoding="cp850",
            errors="ignore"
        )

        output = result.stdout

        match = re.search(r"Zeit[=<]\s*(\d+)\s*ms", output)
        if match:
            return float(match.group(1))

        return None

    except Exception:
        return None


def print_stats(values):
    if len(values) < 2:
        return

    avg = statistics.mean(values)
    jitter = statistics.pstdev(values)

    print("AVG:", round(avg, 1),
          "JITTER:", round(jitter, 1),
          "MIN:", round(min(values), 1),
          "MAX:", round(max(values), 1))


def main():
    print("Ping monitor started")
    print("Target:", TARGET)

    while True:
        latency = ping_once(TARGET)

        if latency is not None:
            latencies.append(latency)
            print(latency, "ms")
        else:
            print("no reply")

        if len(latencies) >= 5:
            print_stats(latencies)

        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()