import asyncio
import math
import moteus
import serial
import matplotlib.pyplot as plt
import numpy as np
import time
import serial


# Prompt the user to enter the motor name
motor_name = input("Enter the motor name: ")

plt.ion()
fig, ax = plt.subplots(2)
line0, = ax[0].plot([],[], 'o')
ax[0].set_xlabel('Current')
ax[0].set_ylabel('Load cell')
ax[0].set_title(f'{motor_name}')  # Use the motor name in the title

line1, = ax[1].plot([],[], 'r-')
ax[1].set_xlabel('Command Current')
ax[1].set_ylabel('Measured Current')
ax[1].set_title(f'{motor_name}')  # Use the motor name in the title


global serial_port

k = last_torque = 0.00
current_step = 0.1 #0.05
max_current = 8
ramp_duration = 0.25
settle_duration = 0.1
read_duration = 0.2


def update_plot(x_data_0, y_data_0, x_data_1, y_data_1):
    # upadate plot 0
    line0.set_xdata(x_data_0)
    line0.set_ydata(y_data_0)
    ax[0].relim()
    ax[0].autoscale_view(True, True, True)

    # update plot 1
    line1.set_xdata(x_data_1)
    line1.set_ydata(y_data_1)
    ax[1].relim()
    ax[1].autoscale_view(True, True, True)

    # draw plot
    plt.draw()
    plt.pause(0.01)


async def set_torque(c, k, last_torque):
    # Gradually increase torque to k following a sin curve
    start_time = time.time()
    load_cell_readings = []
    torque_readings = []
    motor_temp_readings = []
    voltage_readings = []
    temperature_readings = []

    while time.time() - start_time < ramp_duration:
        elapsed = time.time() - start_time
        torque = last_torque + (k-last_torque) * (math.sin(math.pi * elapsed/(2*ramp_duration)))
        await c.set_current(d_A=0, q_A=1*torque)
 
    start_time = time.time()
    while time.time() - start_time < settle_duration:
        await c.set_current(d_A=0, q_A=1*k)

    start_time = time.time()
    while time.time() - start_time < read_duration:
        state = await c.set_current(d_A=0, q_A=1*k, query=True)
        load_cell = await read_load_cell()   

        measured_current = state.values[moteus.Register.Q_CURRENT]
        measured_motor_temp = state.values[moteus.Register.MOTOR_TEMPERATURE]
        measured_voltage = state.values[moteus.Register.VOLTAGE]
        measured_temperature = state.values[moteus.Register.TEMPERATURE]
             
        load_cell_readings.append(load_cell) 
        torque_readings.append(measured_current)
        motor_temp_readings.append(measured_motor_temp)
        voltage_readings.append(measured_voltage)
        temperature_readings.append(measured_temperature)

    # Return a dictionary with all the readings
    return {
        "load_cell_readings": load_cell_readings,
        "torque_readings": torque_readings,
        "motor_temp_readings": motor_temp_readings,
        "voltage_readings": voltage_readings,
        "temperature_readings": temperature_readings
    }


async def read_load_cell():
    serial_port.flushInput()

    send_comand("READ")
    while serial_port.inWaiting() == 0:
        line = serial_port.readline().decode('utf-8').rstrip()
        try:
            return int(line)
        except:
            print(line)
            pass
    
def start_load_cell():
    serial_port.flushInput()

    send_comand("START")
    while serial_port.inWaiting() == 0:
        line = serial_port.readline().decode('utf-8').rstrip()
        return line


def send_comand(command):
    serial_port.write(f"{command}\n".encode())


async def main():
    global serial_port, k, last_torque

    # Initialize the serial port & load cell
    try:
        serial_port = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
        print("Initializing load cell...")
        start_load_cell()
        time.sleep(4)

    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        return
    
    qr = moteus.QueryResolution()
    qr.q_current = moteus.F32
    qr.motor_temperature = moteus.F32
    c = moteus.Controller(id=3, query_resolution=qr) 
    await c.set_stop()

    torque_values = []
    torque_values_compare = []

    with open(f"tests/{motor_name}_results.txt", "w") as file:
        # Save constant parameters only once at the top of the file
        file.write(f"ramp_duration: {ramp_duration}, settle_duration: {settle_duration}, read_duration: {read_duration}, current_step: {current_step}, max_current: {max_current}\n")

        while True:
            data = await set_torque(c, k, last_torque)

            # Extract lists from the dictionary
            load_cell_readings = data["load_cell_readings"]
            torque_readings = data["torque_readings"]
            motor_temp_readings = data["motor_temp_readings"]
            voltage_readings = data["voltage_readings"]
            temperature_readings = data["temperature_readings"]

            # Calculate averages
            average_load_cell_reading = sum(load_cell_readings) / len(load_cell_readings) if load_cell_readings else 0
            average_torque_reading = -1 * sum(torque_readings) / len(torque_readings) if torque_readings else 0
            average_motor_temp = sum(motor_temp_readings) / len(motor_temp_readings) if motor_temp_readings else 0
            average_voltage = sum(voltage_readings) / len(voltage_readings) if voltage_readings else 0
            average_temperature = sum(temperature_readings) / len(temperature_readings) if temperature_readings else 0

            # Construct data dictionary for iteration data
            iteration_data_dict = {
                "torque": k,
                "average_load_cell": average_load_cell_reading,
                "average_torque": average_torque_reading,
                "average_motor_temp": average_motor_temp,
                "average_voltage": average_voltage,
                "average_temperature": average_temperature
            }

            # Write iteration data to file
            file.write(str(iteration_data_dict) + "\n")

            # Print the current iteration data
            print(f"Current: {k}, Torque: {average_torque_reading}, Load Cell: {average_load_cell_reading}, Motor Temp: {average_motor_temp}, Voltage: {average_voltage}, Temperature: {average_temperature}")

            # Update the plot data
            torque_values.append((average_torque_reading, average_load_cell_reading))
            ks, readings = zip(*torque_values) if torque_values else ([], [])

            torque_values_compare.append((average_torque_reading, k))
            torque_read, current_sent = zip(*torque_values_compare) if torque_values_compare else ([], [])

            update_plot(ks, readings, current_sent, torque_read)

            # Update the last_torque and increment k
            last_torque = k
            k += current_step

            # Check if the current exceeds the maximum limit
            if k > max_current:
                break

    # Stop motor 
    load_cell_readings = await c.set_current(d_A=0, q_A=0)
    
    # Write results to a text file
    with open(f"{motor_name}_results.txt", "w") as file:
        file.write("Torque, Load Cell\n")
        for torque, reading in torque_values:
            file.write(f"{torque}, {reading}\n")

    # Keep the plot open until manually closed
    plt.ioff()
    plt.show()

if __name__ == '__main__':
    asyncio.run(main())
