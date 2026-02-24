"""
Self-measurement of rotor inertia using motor - FIXED VERSION
"""
import moteus
import asyncio
import math
import numpy as np
import matplotlib.pyplot as plt

async def measure_inertia():
    CONTROLLER_ID = 3
    
    # Motor constants from calibration
    MOTOR_KV = 22.428579330444336  # RPM/V
    
    # Derive Kt from Kv
    # Kv is in RPM/V, Kt is in Nm/A
    # They are inversely related: Kt = 1/Kv when converted to consistent units
    # Kt [Nm/A] = 60 / (2 * π * Kv[RPM/V])
    MOTOR_KT = 60 / (2 * math.pi * MOTOR_KV)
    TEST_CURRENT = 1.0  # Increase to 4A for clearer signal
    
    query_resolution = moteus.QueryResolution()
    query_resolution._extra = {
        moteus.Register.VELOCITY: moteus.F32,
        moteus.Register.Q_CURRENT: moteus.F32,
        moteus.Register.MODE: moteus.INT8,
    }
    
    controller = moteus.Controller(id=CONTROLLER_ID, query_resolution=query_resolution)
    
    print("Measuring rotor inertia...")
    print("Make sure motor can spin freely with NO load attached!")
    print("Motor will spin up then brake automatically.")
    input("Press Enter when ready...")
    
    # FORCE MOTOR TO MODE 5
    print("Forcing motor to Mode 5 (Position Control)...")
    
    # Step 1: Stop first
    await controller.set_stop()
    await asyncio.sleep(0.3)
    
    # Step 2: Enable with position command multiple times to ensure it sticks
    for i in range(3):
        result = await controller.set_position(
            position=math.nan,
            velocity=0,
            maximum_torque=0.5,
            query=True
        )
        mode = result.values.get(moteus.Register.MODE, -1)
        print(f"  Attempt {i+1}: Mode = {mode}")
        
        if mode == 5:
            print("✓ Motor in Mode 5 (Position Control)")
            break
        
        await asyncio.sleep(0.1)
    else:
        print("✗ Failed to enter Mode 5!")
        print("  Try power cycling the controller and run again.")
        return None
    
    await asyncio.sleep(0.2)
    
    times = []
    velocities = []
    currents = []
    modes = []
    
    print(f"Applying {TEST_CURRENT}A acceleration...")
    start_time = asyncio.get_event_loop().time()
    
    # Acceleration phase - use velocity mode for constant acceleration
    target_velocity = 0.0
    accel_duration = 1.0  # 1 second acceleration
    
    while asyncio.get_event_loop().time() - start_time < accel_duration:
        elapsed = asyncio.get_event_loop().time() - start_time
        
        # Ramp up velocity target to create constant torque need
        target_velocity = elapsed * 2.0  # Accelerate at 2 rev/s²
        
        result = await controller.set_position(
            position=math.nan,  # Don't control position
            velocity=target_velocity,  # Control velocity
            velocity_limit=10.0,  # Allow high velocity
            accel_limit=5.0,  # Accel limit
            maximum_torque=TEST_CURRENT * MOTOR_KT,  # Limit max torque
            query=True
        )
        
        t = asyncio.get_event_loop().time() - start_time
        vel = result.values[moteus.Register.VELOCITY] * 2 * math.pi  # rad/s
        curr = result.values.get(moteus.Register.Q_CURRENT, 0)
        mode = result.values.get(moteus.Register.MODE, 0)
        
        times.append(t)
        velocities.append(vel)
        currents.append(curr)
        modes.append(mode)
        
        # Check if mode changed during test
        if mode != 5:
            print(f"\n⚠ WARNING: Mode changed to {mode} at t={t:.3f}s")
        
        await asyncio.sleep(0.002)  # 2ms sampling
    
    print("Braking...")
    await controller.set_stop()
    await asyncio.sleep(0.5)
    
    # Convert to numpy arrays
    times = np.array(times)
    velocities = np.array(velocities)
    currents = np.array(currents)
    modes = np.array(modes)
    
    # Check if mode stayed at 5
    mode_changes = np.where(modes != 5)[0]
    if len(mode_changes) > 0:
        print(f"\n⚠ Mode changed during test at {len(mode_changes)} points!")
        print(f"  Unique modes seen: {np.unique(modes)}")
    
    # Find region where current is stable and positive
    stable_mask = (currents > 0.5) & (currents < TEST_CURRENT * 1.2)
    
    if np.sum(stable_mask) < 10:
        print("\nERROR: Not enough stable current data!")
        print(f"Current range: {currents.min():.3f} to {currents.max():.3f} A")
        print("Motor may not have accelerated properly.")
        print("\nTroubleshooting:")
        print("1. Check motor is in mode 5 (position/velocity control)")
        print("2. Increase TEST_CURRENT to 5-6A")
        print("3. Make sure motor shaft spins freely")
        return None
    
    stable_times = times[stable_mask]
    stable_velocities = velocities[stable_mask]
    stable_currents = currents[stable_mask]
    
    # Linear fit to get acceleration
    coeffs = np.polyfit(stable_times, stable_velocities, 1)
    acceleration = coeffs[0]  # rad/s²
    
    # Average torque during stable period
    avg_current = np.mean(stable_currents)
    applied_torque = avg_current * MOTOR_KT
    
    # I = T / α
    if abs(acceleration) < 0.1:
        print("\nERROR: Acceleration too small!")
        print("Motor didn't accelerate properly.")
        return None
    
    measured_inertia = applied_torque / acceleration
    
    print("\n" + "="*60)
    print("INERTIA MEASUREMENT RESULTS")
    print("="*60)
    print(f"Applied Current:        {avg_current:.3f} A")
    print(f"Applied Torque:         {applied_torque:.4f} Nm")
    print(f"Measured Acceleration:  {acceleration:.2f} rad/s²")
    print(f"Calculated Inertia:     {measured_inertia:.6f} kg·m²")
    print(f"                        ({measured_inertia * 1e6:.2f} g·cm²)")
    print(f"Data points used:       {len(stable_times)}")
    print("="*60)
    
    # Sanity check
    if measured_inertia < 0.00001 or measured_inertia > 0.01:
        print("\nWARNING: Inertia value seems unusual!")
        print("Typical small BLDC: 0.0001 - 0.001 kg·m²")
    
    # Plot for verification
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    ax1.plot(times, currents, 'b-', label='Measured Current')
    ax1.axhline(y=TEST_CURRENT, color='r', linestyle='--', label=f'Target: {TEST_CURRENT}A')
    ax1.fill_between(stable_times, 0, TEST_CURRENT * 1.5, alpha=0.2, color='green', label='Stable Region')
    ax1.set_ylabel('Current (A)')
    ax1.set_xlabel('Time (s)')
    ax1.set_title('Current vs Time')
    ax1.legend()
    ax1.grid(True)
    
    ax2.plot(times, velocities, 'b.', alpha=0.5, label='Measured Velocity')
    ax2.plot(stable_times, stable_velocities, 'g.', alpha=0.8, label='Stable Region')
    ax2.plot(times, coeffs[0] * times + coeffs[1], 'r-', linewidth=2, 
             label=f'Fit: α={acceleration:.2f} rad/s²')
    ax2.set_ylabel('Velocity (rad/s)')
    ax2.set_xlabel('Time (s)')
    ax2.set_title('Velocity vs Time for Inertia Measurement')
    ax2.legend()
    ax2.grid(True)
    
    plt.tight_layout()
    plt.savefig('inertia_measurement.png', dpi=150)
    print("\nPlot saved: inertia_measurement.png")
    plt.close()
    
    return measured_inertia

if __name__ == "__main__":
    asyncio.run(measure_inertia())