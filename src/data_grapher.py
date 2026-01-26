"""
Motor Performance Analysis - PID vs Raw Power Supply
"""
import matplotlib.pyplot as plt
import numpy as np

# PID Control @ 50V Max data
pid_amps = np.array([1.236, 2.346, 2.971, 4.665, 5.826, 6.668])
pid_voltage = np.array([6.5, 10.7, 13.6, 22.8, 29.2, 37.7])
pid_torque_moteus = np.array([0.472, 0.895, 1.14, 1.781, 2.214, 2.35])
pid_torque_scale = np.array([0.4527315, 0.905463, 1.323369, 1.601973, 2.08953, 1.9154025])
pid_power = np.array([8.034, 25.1022, 40.4056, 106.362, 170.1192, 251.3836])
pid_weight = np.array([1300, 2600, 3800, 4600, 6000, 5500])

# Raw Power Supply data
raw_amps = np.array([1, 2, 2.25, 2.375, 2.5, 2.625, 2.75, 3, 3.5, 4])
raw_voltage = np.array([5.5, 12.4, 13.9, 16.3, 16.5, 18.3, 19.7, 23, 29.7, 39.9])
raw_torque_scale = np.array([0.4527315, 0.905463, 1.0099395, 1.09700325, 1.044765, 
                              1.114416, 1.1492415, 1.253718, 1.39302, 1.4974965])
raw_power = np.array([5.5, 24.8, 31.275, 38.7125, 41.25, 48.0375, 54.175, 69, 103.95, 159.6])
raw_weight = np.array([1300, 2600, 2900, 3150, 3000, 3200, 3300, 3600, 4000, 4300])

# Create figure with 2 subplots
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

# Graph 1: Torque vs Current (Magnetic Saturation Comparison)
ax1.plot(pid_amps, pid_torque_moteus, 'b-o', linewidth=2.5, markersize=10, 
         label='PID - Moteus Reported', alpha=0.8)
ax1.plot(pid_amps, pid_torque_scale, 'c-^', linewidth=2.5, markersize=10, 
         label='PID - Fish Scale Measured', alpha=0.8)
ax1.plot(raw_amps, raw_torque_scale, 'r-s', linewidth=2.5, markersize=10, 
         label='Raw Power Supply', alpha=0.8)

# Add ideal linear line for reference (Kt = 0.441 Nm/A)
max_current = max(max(pid_amps), max(raw_amps))
ideal_current = np.linspace(0, max_current, 100)
ideal_torque = ideal_current * 0.441  # Using Kt from calibration
ax1.plot(ideal_current, ideal_torque, 'g--', linewidth=2, alpha=0.6, 
         label='Ideal Linear (Kt=0.441 Nm/A)')

ax1.set_xlabel('Current (A)', fontsize=13, fontweight='bold')
ax1.set_ylabel('Torque (Nm)', fontsize=13, fontweight='bold')
ax1.set_title('Magnetic Saturation Comparison\nTorque vs Current', 
              fontsize=15, fontweight='bold')
ax1.grid(True, alpha=0.3, linestyle='--')
ax1.legend(fontsize=10, loc='upper left')
ax1.set_xlim(0, max_current * 1.05)
ax1.set_ylim(0, max(max(pid_torque_scale), max(raw_torque_scale)) * 1.1)

# Graph 2: Power vs Current
ax2.plot(pid_amps, pid_power, 'b-o', linewidth=2.5, markersize=10, 
         label='PID Control @ 50V', alpha=0.8)
ax2.plot(raw_amps, raw_power, 'r-s', linewidth=2.5, markersize=10, 
         label='Raw Power Supply', alpha=0.8)

ax2.set_xlabel('Current (A)', fontsize=13, fontweight='bold')
ax2.set_ylabel('Power (W)', fontsize=13, fontweight='bold')
ax2.set_title('Power Consumption Comparison\nPower vs Current', 
              fontsize=15, fontweight='bold')
ax2.grid(True, alpha=0.3, linestyle='--')
ax2.legend(fontsize=11, loc='upper left')
ax2.set_xlim(0, max_current * 1.05)
ax2.set_ylim(0, max(max(pid_power), max(raw_power)) * 1.1)

plt.tight_layout()
plt.savefig('./motor_performance_comparison.png', dpi=300, bbox_inches='tight')
plt.close()

# Create summary statistics
print("="*70)
print("MOTOR PERFORMANCE ANALYSIS - GL60 @ 35.5mm Radius")
print("="*70)
print("\nPID Control @ 50V Max:")
print(f"  Max Current:           {max(pid_amps):.3f} A")
print(f"  Max Torque (Moteus):   {max(pid_torque_moteus):.3f} Nm")
print(f"  Max Torque (Scale):    {max(pid_torque_scale):.3f} Nm")
print(f"  Torque Measurement Δ:  {abs(max(pid_torque_moteus) - max(pid_torque_scale)):.3f} Nm")
print(f"  Max Power:             {max(pid_power):.1f} W")
print(f"  Max Weight:            {max(pid_weight)} g")
print(f"  Efficiency:            {max(pid_torque_scale)/max(pid_amps):.3f} Nm/A")

print(f"\nRaw Power Supply:")
print(f"  Max Current:           {max(raw_amps):.3f} A")
print(f"  Max Torque (Scale):    {max(raw_torque_scale):.3f} Nm")
print(f"  Max Power:             {max(raw_power):.1f} W")
print(f"  Max Weight:            {max(raw_weight)} g")
print(f"  Efficiency:            {max(raw_torque_scale)/max(raw_amps):.3f} Nm/A")

print("\n" + "="*70)
print("KEY OBSERVATIONS:")
print("="*70)
print(f"PID Control achieves {max(pid_weight)/max(raw_weight)*100:.1f}% more lifting capacity")
print(f"PID Control uses {max(pid_amps)/max(raw_amps):.1f}x more current")
print(f"PID Control delivers {max(pid_torque_scale)/max(raw_torque_scale)*100:.1f}% more torque")
print(f"Moteus torque readings are {(max(pid_torque_moteus)/max(pid_torque_scale))*100:.1f}% of scale measurements")
print("="*70)

print("\nGraphs saved!")