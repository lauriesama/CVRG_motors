"""
Moteus Motor Current Hold Test - WITH DUTY CYCLE, MOTOR VOLTAGE, AND TEMPERATURE
"""
import moteus
import asyncio
import math
import csv
from datetime import datetime
import matplotlib.pyplot as plt

async def main():
    CONTROLLER_ID = 1
    DESIRED_MAX_CURRENT = 7 # Amps
    DURATION = 5
    
    # Motor constants from calibration
    MOTOR_KT_GL40 = 67.95806766863022  # RPM/V
    MOTOR_KT_GL60 = 21.672020187243888
    MOTOR_KV = MOTOR_KT_GL60
    
    # Derive Kt from Kv
    # Kv is in RPM/V, Kt is in Nm/A
    # They are inversely related: Kt = 1/Kv when converted to consistent units
    # Kt [Nm/A] = 60 / (2 * π * Kv[RPM/V])
    MOTOR_KT = 60 / (2 * math.pi * MOTOR_KV)
    
    HOLD_TORQUE = DESIRED_MAX_CURRENT * MOTOR_KT  # Convert amps to Nm
    
    # Query resolution to request current, voltage, power, and temperature values
    query_resolution = moteus.QueryResolution()
    query_resolution._extra = {
        moteus.Register.Q_CURRENT: moteus.F32,
        moteus.Register.VOLTAGE: moteus.F32,
        moteus.Register.POWER: moteus.F32,
        moteus.Register.MOTOR_TEMPERATURE: moteus.F32,
        moteus.Register.TEMPERATURE: moteus.F32,
        moteus.Register.FAULT: moteus.INT32,
        moteus.Register.MODE: moteus.INT8,
    }
    
    controller = moteus.Controller(id=CONTROLLER_ID, query_resolution=query_resolution)
    
    state = await controller.query()
    target_position = state.values[moteus.Register.POSITION]
    initial_motor_temp = state.values.get(moteus.Register.MOTOR_TEMPERATURE, 0.0)
    initial_controller_temp = state.values.get(moteus.Register.TEMPERATURE, 0.0)
    
    print(f"Holding at position {target_position:.3f}")
    print(f"Max current: {DESIRED_MAX_CURRENT}A -> Max torque: {HOLD_TORQUE:.2f} Nm")
    print(f"Initial motor temperature: {initial_motor_temp:.1f}°C")
    print(f"Initial controller temperature: {initial_controller_temp:.1f}°C")
    print("Try to rotate the motor!")
    
    # Create timestamp for all files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Prepare CSV filename (will be created later if user wants to save)
    csv_filename = f"{timestamp}_{DESIRED_MAX_CURRENT}A_current_log.csv"
    print(f"Will log to: {csv_filename} (if saved)\n")
    
    # Lists to store measurements
    torque_readings = []
    current_readings = []
    motor_voltage_readings = []
    motor_temperature_readings = []
    controller_temperature_readings = []
    time_log = []
    duty_cycle_log = []
    bus_voltage_log = []
    position_log = []
    power_log = []
    mode_log = []
    fault_log = []
    
    end_time = asyncio.get_event_loop().time() + DURATION
    start_time = asyncio.get_event_loop().time()
    last_print = asyncio.get_event_loop().time()
    
    while asyncio.get_event_loop().time() < end_time:
        state = await controller.set_position(
            position=target_position,
            maximum_torque=HOLD_TORQUE,
            query=True
        )
        
        # Collect measurements
        torque = state.values[moteus.Register.TORQUE]
        q_current = state.values.get(moteus.Register.Q_CURRENT, 0.0)
        bus_voltage = state.values.get(moteus.Register.VOLTAGE, 0.0)
        power = state.values.get(moteus.Register.POWER, 0.0)
        motor_temperature = state.values.get(moteus.Register.MOTOR_TEMPERATURE, 0.0)
        controller_temperature = state.values.get(moteus.Register.TEMPERATURE, 0.0)
        fault = state.values.get(moteus.Register.FAULT, 0)
        mode = state.values.get(moteus.Register.MODE, 0)
        
        # Calculate duty cycle and effective motor voltage
        if q_current > 0.01 and bus_voltage > 0:  # Avoid division by zero
            motor_voltage = power / q_current  # Effective voltage at motor
            duty_cycle = motor_voltage / bus_voltage
        else:
            motor_voltage = 0.0
            duty_cycle = 0.0
        
        torque_readings.append(torque)
        current_readings.append(q_current)
        motor_voltage_readings.append(motor_voltage)
        motor_temperature_readings.append(motor_temperature)
        controller_temperature_readings.append(controller_temperature)
        
        # Store all data in memory
        elapsed_time = asyncio.get_event_loop().time() - start_time
        time_log.append(elapsed_time)
        duty_cycle_log.append(duty_cycle)
        bus_voltage_log.append(bus_voltage)
        current_pos = state.values[moteus.Register.POSITION]
        position_log.append(current_pos)
        power_log.append(power)
        mode_log.append(mode)
        fault_log.append(fault)
        
        if asyncio.get_event_loop().time() - last_print > 0.5:
            error = target_position - current_pos
            print(f"Pos: {current_pos:.3f} | Error: {error:.4f} | "
                  f"Torque: {torque:.2f}Nm | Q: {q_current:.2f}A | "
                  f"V_motor: {motor_voltage:.1f}V | Duty: {duty_cycle*100:.1f}% | "
                  f"Temp M: {motor_temperature:.1f}°C | Temp C: {controller_temperature:.1f}°C | "
                  f"Mode: {mode} | Fault: {fault}")
            last_print = asyncio.get_event_loop().time()
        
    
    await controller.set_stop()
    print("\nTest complete!")
    
    # Calculate and display peaks
    total_samples = len(time_log)
    actual_duration = time_log[-1] if time_log else DURATION
    sample_rate = total_samples / actual_duration if actual_duration > 0 else 0
    
    # Build summary statistics string
    summary_text = []
    summary_text.append("=" * 60)
    summary_text.append("STATISTICS")
    summary_text.append("=" * 60)
    summary_text.append(f"Test Configuration:")
    summary_text.append(f"  Target Current:          {DESIRED_MAX_CURRENT} A")
    summary_text.append(f"  Target Torque:           {HOLD_TORQUE:.2f} Nm")
    summary_text.append(f"  Test Duration:           {DURATION} s")
    summary_text.append(f"  Motor Kt:                {MOTOR_KT:.4f} Nm/A")
    summary_text.append(f"  Motor Kv:                {MOTOR_KV:.2f} RPM/V")
    summary_text.append("")
    summary_text.append(f"Data Collection:")
    summary_text.append(f"  Samples Collected:       {total_samples}")
    summary_text.append(f"  Sample Rate:             {sample_rate:.1f} Hz")
    summary_text.append(f"  Actual Duration:         {actual_duration:.2f} s")
    summary_text.append("")
    summary_text.append(f"Electrical Measurements:")
    summary_text.append(f"  Peak Motor Voltage:      {max(motor_voltage_readings):.1f} V")
    summary_text.append(f"  Average Motor Voltage:   {sum(motor_voltage_readings)/len(motor_voltage_readings):.1f} V")
    summary_text.append(f"  Peak Current:            {max(current_readings):.3f} A")
    summary_text.append(f"  Average Current:         {sum(current_readings)/len(current_readings):.3f} A")
    summary_text.append(f"  Peak Duty Cycle:         {max(duty_cycle_log)*100:.1f} %")
    summary_text.append(f"  Average Duty Cycle:      {sum(duty_cycle_log)/len(duty_cycle_log)*100:.1f} %")
    summary_text.append("")
    summary_text.append(f"Torque Performance:")
    summary_text.append(f"  Peak Torque:             {max(torque_readings):.3f} Nm")
    summary_text.append(f"  Average Torque:          {sum(torque_readings)/len(torque_readings):.3f} Nm")
    summary_text.append("")
    summary_text.append(f"Thermal Performance:")
    summary_text.append(f"  Initial Motor Temp:      {initial_motor_temp:.1f}°C")
    summary_text.append(f"  Peak Motor Temp:         {max(motor_temperature_readings):.1f}°C")
    summary_text.append(f"  Motor Temp Rise:         {max(motor_temperature_readings) - initial_motor_temp:.1f}°C")
    summary_text.append(f"  Initial Controller Temp: {initial_controller_temp:.1f}°C")
    summary_text.append(f"  Peak Controller Temp:    {max(controller_temperature_readings):.1f}°C")
    summary_text.append(f"  Controller Temp Rise:    {max(controller_temperature_readings) - initial_controller_temp:.1f}°C")
    summary_text.append("=" * 60)
    
    # Print to console
    print()
    for line in summary_text:
        print(line)
    
    # Ask user if they want to save the data
    print("\n" + "=" * 60)
    save_response = input("Save data files? (y/enter to save, n to discard): ").strip().lower()
    
    if save_response == '' or save_response == 'y' or save_response == 'yes':
        # Create and write CSV file
        csv_file = open(csv_filename, 'w', newline='')
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(['time_s', 'duty_cycle', 'motor_voltage_v', 'bus_voltage_v', 
                             'current_a', 'torque_nm', 'motor_temperature_c', 'controller_temperature_c', 
                             'position', 'power_w', 'mode', 'fault'])
        
        # Write all stored data to CSV
        for i in range(len(time_log)):
            csv_writer.writerow([
                f"{time_log[i]:.4f}",
                f"{duty_cycle_log[i]:.6f}",
                f"{motor_voltage_readings[i]:.4f}",
                f"{bus_voltage_log[i]:.4f}",
                f"{current_readings[i]:.4f}",
                f"{torque_readings[i]:.4f}",
                f"{motor_temperature_readings[i]:.4f}",
                f"{controller_temperature_readings[i]:.4f}",
                f"{position_log[i]:.6f}",
                f"{power_log[i]:.4f}",
                f"{mode_log[i]}",
                f"{fault_log[i]}"
            ])
        csv_file.close()
        print(f"CSV saved to: {csv_filename}")
        
        # Save summary to file
        summary_filename = f"{timestamp}_{DESIRED_MAX_CURRENT}A_summary.txt"
        with open(summary_filename, 'w') as summary_file:
            summary_file.write('\n'.join(summary_text))
        print(f"Summary saved to: {summary_filename}")
        
        # Generate current plot
        print("Generating current plot...")
        plt.figure(figsize=(12, 6))
        plt.plot(time_log, current_readings, linewidth=0.8, color='blue')
        plt.xlabel('Time (s)', fontsize=12)
        plt.ylabel('Q-axis Current (A)', fontsize=12)
        plt.title(f'Motor Q-axis Current Over Time - {DESIRED_MAX_CURRENT}A Hold Test', fontsize=14)
        plt.grid(True, alpha=0.3)
        plt.axhline(y=DESIRED_MAX_CURRENT, color='r', linestyle='--', linewidth=1, label=f'Target: {DESIRED_MAX_CURRENT}A')
        plt.legend()
        plt.tight_layout()
        
        # Save plot
        plot_filename = f"{timestamp}_{DESIRED_MAX_CURRENT}A_current_plot.png"
        plt.savefig(plot_filename, dpi=150)
        print(f"Plot saved to: {plot_filename}")
        plt.close()
        
        print(f"\nAll data saved:")
        print(f"  - CSV: {csv_filename}")
        print(f"  - Summary: {summary_filename}")
        print(f"  - Plot: {plot_filename}")
    else:
        print("Data discarded. No files saved.")

if __name__ == "__main__":
    asyncio.run(main())