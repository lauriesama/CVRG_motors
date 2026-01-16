import serial
import time
from collections import deque

PORT = "/dev/ttyUSB0"   # change if needed
BAUD = 9600
WINDOW = 15

ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)  # Arduino reset delay

def send(cmd):
    ser.write((cmd + "\n").encode("utf-8"))
    time.sleep(0.02)
    return ser.readline().decode("utf-8").strip()

buffer = deque(maxlen=WINDOW)

print(send("START"))
print(f"Reading load cell values (rolling average over {WINDOW} samples):")

try:
    while True:
        response = send("READ")
        if response:
            try:
                value = float(response)
                buffer.append(value)

                avg = sum(buffer) / len(buffer)
                print(f"raw: {value:.3f}  avg: {avg:.3f}")
            except ValueError:
                # Ignore non-numeric messages like "HX711 not found."
                pass

        time.sleep(0.05)

except KeyboardInterrupt:
    ser.close()
