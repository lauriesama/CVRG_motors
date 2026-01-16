import asyncio
import math
import moteus
import serial
import matplotlib.pyplot as plt
import numpy as np
import time
import serial

global serial_port

async def read_load_cell_async():
    load_cell = read_load_cell()
    while load_cell == None:
        load_cell = read_load_cell()

    return load_cell

async def set_torque(c, k, load_cell_readings):
    # Gradually increase torque to k following a cosine curve
    start_time = time.time()
    ramp_duration = 0.5
    settle_duration = 0.25
    read_duration = 0.1

    while time.time() - start_time < ramp_duration:
        elapsed = time.time() - start_time
        torque = k * (math.sin(math.pi * elapsed/(2*ramp_duration)))
        await c.set_current(d_A=0, q_A=-1*torque)
 
    start_time = time.time()
    while time.time() - start_time < settle_duration:
        await c.set_current(d_A=0, q_A=-1*k)
        load_cell = await read_load_cell_async()
        load_cell_readings.append(load_cell)

    start_time = time.time()
    serial_port.flushInput()   #to remove and fix    
    serial_port.readline()  
    while time.time() - start_time < read_duration:
        await c.set_current(d_A=0, q_A=-1*k)
        load_cell = await read_load_cell_async()
        load_cell_readings.append(load_cell) 

    start_time = time.time()
    while time.time() - start_time < ramp_duration:
        torque = k * (1 - math.sin(math.pi * (elapsed-2*ramp_duration)/(2*ramp_duration)))
        await c.set_current(d_A=0, q_A=-1*torque)


def read_load_cell():
    if serial_port.in_waiting > 0:
        line = serial_port.readline().decode().strip()
        try:
            return float(line)  # Assuming the Arduino sends float values
        except ValueError:
            print("Error: Invalid data received:", line)
            return None
    return None


async def main():
    global serial_port

    # Initialize the serial port
    try:
        serial_port = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
        print("Initializing serial port...")
        time.sleep(5)
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        return

    c = moteus.Controller()
    await c.set_stop()
    load_cell_readings = []
    torque_values = []
    k = 0.00
    step_t = 0.01
    max_t = 1.5

    print("Starting testing!")
    while True:
        await set_torque(c, k, load_cell_readings)
        average_reading = sum(load_cell_readings) / len(load_cell_readings)
        print(f"Torque: {k}, Load Cell: {average_reading}")

        torque_values.append((k, average_reading))
        load_cell_readings.clear()
        k += step_t # Increment k

        # Prompt the user to continue or not

        #continue_prompt = input("Continue? (y/n): ")
        #if continue_prompt.lower() != 'y':
        #    break
        
        if k > max_t:
            break

    # Plotting
    ks, readings = zip(*torque_values)
    plt.plot(ks, readings)
    plt.xlabel('Torque (k)')
    plt.ylabel('Average Load Cell Reading')
    plt.title('Load Cell Reading vs Torque')
    plt.show()

if __name__ == '__main__':
    asyncio.run(main())
