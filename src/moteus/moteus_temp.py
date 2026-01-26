#!/usr/bin/env python3
"""
Simple moteus temperature reader
Continuously reads and prints the temperature sensor value
"""
import asyncio
import moteus
import math

async def main():
    # Controller ID
    CONTROLLER_ID = 3
    
    # Query resolution to request motor temperature
    query_resolution = moteus.QueryResolution()
    query_resolution._extra = {
        moteus.Register.MOTOR_TEMPERATURE: moteus.F32,
        moteus.Register.TEMPERATURE: moteus.F32,
        moteus.Register.FAULT: moteus.INT32,
        moteus.Register.MODE: moteus.INT8,
    }
    
    # Create a moteus controller instance
    controller = moteus.Controller(id=CONTROLLER_ID, query_resolution=query_resolution)
    
    # RE-ENABLE THE MOTOR
    print("Re-enabling motor...")
    await controller.set_position(position=math.nan, query=True)
    print("Motor enabled!\n")
    
    print("Starting moteus temperature reader...")
    print("Reading EXTERNAL motor temperature sensor")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            # Query the controller for temperature data
            result = await controller.query()
            
            # Get values
            motor_temp = result.values.get(moteus.Register.MOTOR_TEMPERATURE, 'N/A')
            controller_temp = result.values.get(moteus.Register.TEMPERATURE, 'N/A')
            fault_code = result.values.get(moteus.Register.FAULT, 0)
            mode = result.values.get(moteus.Register.MODE, 'N/A')
            
            # Print the temperatures and status
            print(f"Motor Temp: {motor_temp}°C | "
                  f"Controller Temp: {controller_temp}°C | "
                  f"Mode: {mode} | "
                  f"Fault: {fault_code}")
            
            # Wait a bit before next reading (adjust as needed)
            await asyncio.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\nStopping temperature reader...")
        await controller.set_stop()

if __name__ == "__main__":
    asyncio.run(main())