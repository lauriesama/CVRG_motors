"""
Moteus Motor Current Range Test - Multiple tests with temperature monitoring
Runs current hold tests from START_CURRENT to END_CURRENT in STEP_CURRENT increments
Waits for motor to cool below 30°C between tests
"""
import moteus
import asyncio
import math
import csv
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import os

async def wait_for_cooldown(controller, max_temp=30.0, check_interval=2.0):
    """
    Wait for motor temperature to drop below max_temp before proceeding.
    Returns the current motor temperature once cool enough.
    """
    print(f"\nWaiting for motor to cool below {max_temp}°C...")
    
    while True:
        state = await controller.query()
        motor_temp = state.values.get(moteus.Register.MOTOR_TEMPERATURE, 0.0)
        controller_temp = state.values.get(moteus.Register.TEMPERATURE, 0.0)
        
        print(f"  Motor: {motor_temp:.1f}°C | Controller: {controller_temp:.1f}°C", end='\r')
        
        if motor_temp < max_temp:
            print(f"\n✓ Motor cooled to {motor_temp:.1f}°C")
            return motor_temp
        
        await asyncio.sleep(check_interval)

async def run_single_test(controller, current_amps, motor_kv, duration, query_resolution):
    """
    Run a single current hold test and return the collected data.
    """
    # Derive Kt from Kv
    MOTOR_KT = 60 / (2 * math.pi * motor_kv)
    HOLD_TORQUE = current_amps * MOTOR_KT
    
    state = await controller.query()
    target_position = state.values[moteus.Register.POSITION]
    initial_motor_temp = state.values.get(moteus.Register.MOTOR_TEMPERATURE, 0.0)
    initial_controller_temp = state.values.get(moteus.Register.TEMPERATURE, 0.0)
    
    print(f"\n{'='*60}")
    print(f"Starting test: {current_amps}A")
    print(f"{'='*60}")
    print(f"Holding at position {target_position:.3f}")
    print(f"Max current: {current_amps}A -> Max torque: {HOLD_TORQUE:.2f} Nm")
    print(f"Initial motor temperature: {initial_motor_temp:.1f}°C")
    print(f"Initial controller temperature: {initial_controller_temp:.1f}°C")
    print(f"Duration: {duration}s")
    print("Try to rotate the motor!")
    
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
    
    end_time = asyncio.get_event_loop().time() + duration
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
        if q_current > 0.01 and bus_voltage > 0:
            motor_voltage = power / q_current
            duty_cycle = motor_voltage / bus_voltage
        else:
            motor_voltage = 0.0
            duty_cycle = 0.0
        
        torque_readings.append(torque)
        current_readings.append(q_current)
        motor_voltage_readings.append(motor_voltage)
        motor_temperature_readings.append(motor_temperature)
        controller_temperature_readings.append(controller_temperature)
        
        # Store all data
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
    
    # Return all collected data
    return {
        'current_amps': current_amps,
        'motor_kt': MOTOR_KT,
        'motor_kv': motor_kv,
        'target_torque': HOLD_TORQUE,
        'duration': duration,
        'initial_motor_temp': initial_motor_temp,
        'initial_controller_temp': initial_controller_temp,
        'time_log': time_log,
        'duty_cycle_log': duty_cycle_log,
        'motor_voltage_readings': motor_voltage_readings,
        'bus_voltage_log': bus_voltage_log,
        'current_readings': current_readings,
        'torque_readings': torque_readings,
        'motor_temperature_readings': motor_temperature_readings,
        'controller_temperature_readings': controller_temperature_readings,
        'position_log': position_log,
        'power_log': power_log,
        'mode_log': mode_log,
        'fault_log': fault_log
    }

def save_test_data(data, timestamp, output_dir):
    """
    Save test data to CSV, summary text file, and plot.
    """
    current_amps = data['current_amps']
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # CSV filename
    csv_filename = os.path.join(output_dir, f"{timestamp}_{current_amps}A_current_log.csv")
    
    # Write CSV
    with open(csv_filename, 'w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(['time_s', 'duty_cycle', 'motor_voltage_v', 'bus_voltage_v', 
                             'current_a', 'torque_nm', 'motor_temperature_c', 'controller_temperature_c', 
                             'position', 'power_w', 'mode', 'fault'])
        
        for i in range(len(data['time_log'])):
            csv_writer.writerow([
                f"{data['time_log'][i]:.4f}",
                f"{data['duty_cycle_log'][i]:.6f}",
                f"{data['motor_voltage_readings'][i]:.4f}",
                f"{data['bus_voltage_log'][i]:.4f}",
                f"{data['current_readings'][i]:.4f}",
                f"{data['torque_readings'][i]:.4f}",
                f"{data['motor_temperature_readings'][i]:.4f}",
                f"{data['controller_temperature_readings'][i]:.4f}",
                f"{data['position_log'][i]:.6f}",
                f"{data['power_log'][i]:.4f}",
                f"{data['mode_log'][i]}",
                f"{data['fault_log'][i]}"
            ])
    
    # Calculate statistics
    total_samples = len(data['time_log'])
    actual_duration = data['time_log'][-1] if data['time_log'] else data['duration']
    sample_rate = total_samples / actual_duration if actual_duration > 0 else 0
    
    # Build summary
    summary_text = []
    summary_text.append("=" * 60)
    summary_text.append(f"STATISTICS - {current_amps}A TEST")
    summary_text.append("=" * 60)
    summary_text.append(f"Test Configuration:")
    summary_text.append(f"  Target Current:          {current_amps} A")
    summary_text.append(f"  Target Torque:           {data['target_torque']:.2f} Nm")
    summary_text.append(f"  Test Duration:           {data['duration']} s")
    summary_text.append(f"  Motor Kt:                {data['motor_kt']:.4f} Nm/A")
    summary_text.append(f"  Motor Kv:                {data['motor_kv']:.2f} RPM/V")
    summary_text.append("")
    summary_text.append(f"Data Collection:")
    summary_text.append(f"  Samples Collected:       {total_samples}")
    summary_text.append(f"  Sample Rate:             {sample_rate:.1f} Hz")
    summary_text.append(f"  Actual Duration:         {actual_duration:.2f} s")
    summary_text.append("")
    summary_text.append(f"Electrical Measurements:")
    summary_text.append(f"  Peak Motor Voltage:      {max(data['motor_voltage_readings']):.1f} V")
    summary_text.append(f"  Average Motor Voltage:   {sum(data['motor_voltage_readings'])/len(data['motor_voltage_readings']):.1f} V")
    summary_text.append(f"  Peak Current:            {max(data['current_readings']):.3f} A")
    summary_text.append(f"  Average Current:         {sum(data['current_readings'])/len(data['current_readings']):.3f} A")
    summary_text.append(f"  Peak Duty Cycle:         {max(data['duty_cycle_log'])*100:.1f} %")
    summary_text.append(f"  Average Duty Cycle:      {sum(data['duty_cycle_log'])/len(data['duty_cycle_log'])*100:.1f} %")
    summary_text.append("")
    summary_text.append(f"Torque Performance:")
    summary_text.append(f"  Peak Torque:             {max(data['torque_readings']):.3f} Nm")
    summary_text.append(f"  Average Torque:          {sum(data['torque_readings'])/len(data['torque_readings']):.3f} Nm")
    summary_text.append("")
    summary_text.append(f"Thermal Performance:")
    summary_text.append(f"  Initial Motor Temp:      {data['initial_motor_temp']:.1f}°C")
    summary_text.append(f"  Peak Motor Temp:         {max(data['motor_temperature_readings']):.1f}°C")
    summary_text.append(f"  Motor Temp Rise:         {max(data['motor_temperature_readings']) - data['initial_motor_temp']:.1f}°C")
    summary_text.append(f"  Initial Controller Temp: {data['initial_controller_temp']:.1f}°C")
    summary_text.append(f"  Peak Controller Temp:    {max(data['controller_temperature_readings']):.1f}°C")
    summary_text.append(f"  Controller Temp Rise:    {max(data['controller_temperature_readings']) - data['initial_controller_temp']:.1f}°C")
    summary_text.append("=" * 60)
    
    # Print to console
    print()
    for line in summary_text:
        print(line)
    
    # Save summary to file
    summary_filename = os.path.join(output_dir, f"{timestamp}_{current_amps}A_summary.txt")
    with open(summary_filename, 'w') as summary_file:
        summary_file.write('\n'.join(summary_text))
    
    # Generate plot
    plt.figure(figsize=(12, 6))
    plt.plot(data['time_log'], data['current_readings'], linewidth=0.8, color='blue')
    plt.xlabel('Time (s)', fontsize=12)
    plt.ylabel('Q-axis Current (A)', fontsize=12)
    plt.title(f'Motor Q-axis Current Over Time - {current_amps}A Hold Test', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.axhline(y=current_amps, color='r', linestyle='--', linewidth=1, label=f'Target: {current_amps}A')
    plt.legend()
    plt.tight_layout()
    
    plot_filename = os.path.join(output_dir, f"{timestamp}_{current_amps}A_current_plot.png")
    plt.savefig(plot_filename, dpi=150)
    plt.close()
    
    print(f"\nData saved:")
    print(f"  - CSV: {csv_filename}")
    print(f"  - Summary: {summary_filename}")
    print(f"  - Plot: {plot_filename}")
    
    return {
        'csv': csv_filename,
        'summary': summary_filename,
        'plot': plot_filename
    }

async def main():
    # ==================== CONFIGURATION ====================
    CONTROLLER_ID = 1
    
    # Test range configuration
    START_CURRENT = 0.5    # Starting current in Amps
    END_CURRENT = 4     # Ending current in Amps
    STEP_CURRENT = 0.5   # Increment in Amps
    
    # Test duration for each current level
    DURATION = 5        # seconds
    
    # Temperature safety
    MAX_TEMP_BEFORE_TEST = 30.0  # °C - motor must be below this to start next test
    
    # Motor constants from calibration
    MOTOR_KT_GL40 = 63.587219136045626  # RPM/V
    MOTOR_KT_GL60 = 21.672020187243888
    MOTOR_KT_GB54_2 = "pee"
    MOTOR_KV = MOTOR_KT_GL60
    
    # Output directory
    OUTPUT_DIR = "moteus_current_tests"
    # =======================================================
    
    print("=" * 60)
    print("MOTEUS CURRENT RANGE TESTER")
    print("=" * 60)
    print(f"Test Configuration:")
    print(f"  Current Range:     {START_CURRENT}A to {END_CURRENT}A")
    print(f"  Step Size:         {STEP_CURRENT}A")
    print(f"  Test Duration:     {DURATION}s per test")
    print(f"  Max Temp (start):  {MAX_TEMP_BEFORE_TEST}°C")
    print(f"  Motor Kv:          {MOTOR_KV:.2f} RPM/V")
    print(f"  Output Directory:  {OUTPUT_DIR}")
    print("=" * 60)
    
    # Calculate number of tests
    num_tests = int((END_CURRENT - START_CURRENT) / STEP_CURRENT) + 1
    test_currents = [START_CURRENT + i * STEP_CURRENT for i in range(num_tests)]
    
    print(f"\nWill run {num_tests} tests at: {', '.join([f'{c}A' for c in test_currents])}")
    
    input("\nPress Enter to begin test sequence...")
    
    # Setup controller
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
    
    # Create master timestamp for this test session
    session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = os.path.join(OUTPUT_DIR, session_timestamp)
    
    # Store all test results
    all_test_data = []
    
    # Run tests
    for test_num, current_amps in enumerate(test_currents, 1):
        print(f"\n{'#'*60}")
        print(f"TEST {test_num}/{num_tests}: {current_amps}A")
        print(f"{'#'*60}")
        
        # Wait for cooldown before test (except first test)
        if test_num > 1:
            await wait_for_cooldown(controller, MAX_TEMP_BEFORE_TEST)
        
        # Ask user to confirm ready
        response = input(f"\nReady to start {current_amps}A test? (Enter to continue, 's' to skip, 'q' to quit): ").strip().lower()
        
        if response == 'q':
            print("Test sequence aborted by user.")
            break
        elif response == 's':
            print(f"Skipping {current_amps}A test.")
            continue
        
        # Run the test
        test_data = await run_single_test(controller, current_amps, MOTOR_KV, DURATION, query_resolution)
        
        # Save the test data
        save_test_data(test_data, session_timestamp, session_dir)
        
        # Store for summary
        all_test_data.append(test_data)
    
    # Generate summary comparison plot
    if len(all_test_data) > 1:
        print(f"\n{'='*60}")
        print("Generating comparison plots...")
        print(f"{'='*60}")
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        for data in all_test_data:
            label = f"{data['current_amps']}A"
            times = np.array(data['time_log'])
            temps = np.array(data['motor_temperature_readings'])
            
            # Current vs time
            ax1.plot(times, data['current_readings'], label=label, linewidth=1.5)
            
            # Temperature vs time - raw data
            line = ax2.plot(times, temps, label=label, linewidth=1.5, alpha=0.7)
            line_color = line[0].get_color()

            # --- Linear fit on the SECOND HALF of the temperature data ---
            half_idx = len(times) // 2
            t_half = times[half_idx:]
            T_half = temps[half_idx:]

            if len(t_half) > 1:
                slope, intercept = np.polyfit(t_half, T_half, 1)
                fit_line = slope * t_half + intercept
                ax2.plot(
                    t_half, fit_line,
                    color=line_color,
                    linewidth=2.5,
                    linestyle='--',
                    label=f"{data['current_amps']}A fit ({slope:.3f}°C/s)"
                )
            
            # Duty cycle vs time
            ax3.plot(times, [d*100 for d in data['duty_cycle_log']], label=label, linewidth=1.5)
            
            # Torque vs time
            ax4.plot(times, data['torque_readings'], label=label, linewidth=1.5)
        
        # Add vertical line at halfway point on temp plot to show fit region
        total_duration = max(d['time_log'][-1] for d in all_test_data)
        ax2.axvline(
            x=total_duration / 2,
            color='black', linestyle=':', linewidth=1.2, alpha=0.5,
            label='Fit start (50%)'
        )

        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('Current (A)')
        ax1.set_title('Q-axis Current Comparison')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        ax2.set_xlabel('Time (s)')
        ax2.set_ylabel('Temperature (°C)')
        ax2.set_title('Motor Temperature Comparison\n(dashed = linear fit on 2nd half)')
        ax2.grid(True, alpha=0.3)
        # Build a cleaner legend - group raw and fit lines by current
        handles, labels = ax2.get_legend_handles_labels()
        ax2.legend(handles, labels, fontsize=7, ncol=2, loc='upper left')
        
        ax3.set_xlabel('Time (s)')
        ax3.set_ylabel('Duty Cycle (%)')
        ax3.set_title('PWM Duty Cycle Comparison')
        ax3.grid(True, alpha=0.3)
        ax3.legend()
        
        ax4.set_xlabel('Time (s)')
        ax4.set_ylabel('Torque (Nm)')
        ax4.set_title('Torque Output Comparison')
        ax4.grid(True, alpha=0.3)
        ax4.legend()
        
        plt.tight_layout()
        comparison_plot = os.path.join(session_dir, f"{session_timestamp}_comparison.png")
        plt.savefig(comparison_plot, dpi=150)
        plt.close()
        print(f"Comparison plot saved to: {comparison_plot}")
        
        # Generate summary statistics table
        summary_table = os.path.join(session_dir, f"{session_timestamp}_summary_table.txt")
        with open(summary_table, 'w') as f:
            f.write("=" * 140 + "\n")
            f.write("CURRENT RANGE TEST SUMMARY\n")
            f.write("=" * 140 + "\n\n")
            f.write(f"{'Current':<10} {'Peak I':<10} {'Avg I':<10} {'Peak T':<10} {'ΔT':<10} {'Peak Duty':<12} {'Avg Duty':<12} {'Peak Torque':<12} {'Temp Rate':<14}\n")
            f.write(f"{'(A)':<10} {'(A)':<10} {'(A)':<10} {'(°C)':<10} {'(°C)':<10} {'(%)':<12} {'(%)':<12} {'(Nm)':<12} {'(°C/s, 2nd½)':<14}\n")
            f.write("-" * 140 + "\n")
            
            for data in all_test_data:
                peak_i = max(data['current_readings'])
                avg_i = sum(data['current_readings']) / len(data['current_readings'])
                peak_temp = max(data['motor_temperature_readings'])
                delta_temp = peak_temp - data['initial_motor_temp']
                peak_duty = max(data['duty_cycle_log']) * 100
                avg_duty = sum(data['duty_cycle_log']) / len(data['duty_cycle_log']) * 100
                peak_torque = max(data['torque_readings'])
                
                # Linear fit on second half for temp rate
                times = np.array(data['time_log'])
                temps = np.array(data['motor_temperature_readings'])
                half_idx = len(times) // 2
                slope, _ = np.polyfit(times[half_idx:], temps[half_idx:], 1)
                
                f.write(f"{data['current_amps']:<10.2f} {peak_i:<10.3f} {avg_i:<10.3f} {peak_temp:<10.1f} {delta_temp:<10.1f} {peak_duty:<12.1f} {avg_duty:<12.1f} {peak_torque:<12.3f} {slope:<14.4f}\n")
            
            f.write("=" * 140 + "\n")
        
        print(f"Summary table saved to: {summary_table}")
    
    print(f"\n{'='*60}")
    print("ALL TESTS COMPLETE!")
    print(f"{'='*60}")
    print(f"Results saved to: {session_dir}")
    print(f"Total tests completed: {len(all_test_data)}/{num_tests}")

if __name__ == "__main__":
    asyncio.run(main())