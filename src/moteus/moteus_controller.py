#!/usr/bin/env python3
"""
Moteus Motor Controller Script - MAXIMUM TORQUE MODE
Locks the motor in place using constant current for maximum holding force.
No encoder required - uses electromagnetic locking.

⚠️  WARNING: This mode continuously draws power and generates heat!
- NO temperature sensor - monitor motor heat manually by touch
- Stop immediately if motor becomes too hot to touch comfortably
- Do not exceed your motor's rated continuous current
- Keep duration SHORT (under 10 seconds) without cooling
"""

import moteus
import asyncio
import logging
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def hold_with_current_timed(
    controller: moteus.Controller,
    holding_current: float,
    duration: float,
    update_rate_hz: float = 50.0
) -> None:
    """
    Lock the motor in place using constant d/q current for maximum holding torque.
    This is like an electromagnetic lock - draws continuous power but provides strong holding.
    
    WARNING: This generates heat! Touch the motor periodically - if too hot to touch, stop.
    
    Args:
        controller (moteus.Controller): The moteus controller instance.
        holding_current (float): Current in Amperes to lock the motor (higher = stronger hold).
        duration (float): Duration to hold in seconds.
        update_rate_hz (float): Rate at which to send commands (default 50Hz).
    """
    loop = asyncio.get_event_loop()
    update_period = 1.0 / update_rate_hz
    
    start_time = loop.time()
    end_time = start_time + duration
    
    logger.info(f"MAXIMUM TORQUE MODE: Locking motor with {holding_current}A for {duration}s")
    logger.warning("This mode generates heat - monitor motor temperature!")
    
    try:
        iteration = 0
        while loop.time() < end_time:
            iter_start = loop.time()
            
            # Apply d and q currents to lock the motor
            # d=0 for max efficiency, q provides the locking torque
            result = await controller.set_current(
                d_A=0.0,
                q_A=holding_current,
                query=True
            )
            
            # Log feedback every 10 iterations (every 0.2s at 50Hz)
            if iteration % 10 == 0 and result:
                voltage = result.values.get(moteus.Register.VOLTAGE, 0)
                logger.info(f"Motor locked - Voltage: {voltage:.1f}V, Time: {loop.time() - start_time:.1f}s")
            
            iteration += 1
            
            # Sleep for remaining time to maintain update rate
            elapsed = loop.time() - iter_start
            sleep_time = max(0, update_period - elapsed)
            await asyncio.sleep(sleep_time)
        
        logger.info("Duration complete, stopping motor")
        
    except Exception as e:
        logger.error(f"Error during motor operation: {e}")
        raise
    
    finally:
        # Always stop the motor, even if there was an error
        try:
            await controller.set_stop()
            logger.info("Motor stopped safely")
        except Exception as e:
            logger.error(f"Error stopping motor: {e}")


async def initialize_controller(
    controller_id: int = 3,
    transport_settings: dict = None
) -> Optional[moteus.Controller]:
    """
    Initialize and test connection to moteus controller.
    
    Args:
        controller_id (int): CAN bus ID of the moteus controller.
        transport_settings (dict): Optional transport configuration.
        
    Returns:
        moteus.Controller if successful, None otherwise.
    """
    try:
        # Create transport if settings provided
        if transport_settings:
            transport = moteus.Transport(**transport_settings)
            controller = moteus.Controller(id=controller_id, transport=transport)
            logger.info(f"Connecting to controller ID {controller_id} with custom transport...")
        else:
            controller = moteus.Controller(id=controller_id)
            logger.info(f"Connecting to controller ID {controller_id} (auto-detect)...")
        
        # Test connection by querying state
        result = await controller.query()
        
        if result:
            logger.info(f"Connection successful! Mode: {result.mode}")
            return controller
        else:
            logger.error("No response from controller")
            return None
            
    except Exception as e:
        logger.error(f"Failed to initialize controller: {e}")
        logger.info("💡 TIP: Run 'python moteus_discover.py' to find your controller!")
        return None


async def main():
    """Main execution function."""
    
    # Configuration
    CONTROLLER_ID = 1
    HOLDING_CURRENT = 3.0  # Amperes - adjust based on your motor's rating!
                           # Typical range: 1-5A for small motors, 5-15A for larger
                           # Check your motor's spec sheet for max continuous current
    DURATION = 4.0         # Duration in seconds
    UPDATE_RATE = 50.0     # Hz
    
    # Transport settings - uncomment and modify if auto-detect doesn't work
    # Option 1: Default (auto-detect) - uncomment the line below
    TRANSPORT_SETTINGS = None
    
    # Option 2: USB with specific port - uncomment and modify the line below
    # TRANSPORT_SETTINGS = {"serial_port": "/dev/ttyACM0"}
    
    # Option 3: CAN socketcan - uncomment and modify the line below
    # TRANSPORT_SETTINGS = {"type": "socketcan", "interface": "can0"}
    
    logger.warning("=" * 70)
    logger.warning("MAXIMUM TORQUE MODE")
    logger.warning(f"Holding current: {HOLDING_CURRENT}A")
    logger.warning("⚠️  NO TEMPERATURE SENSOR - Monitor motor heat manually!")
    logger.warning("Touch the motor periodically - if too hot to touch, STOP immediately")
    logger.warning("This will generate heat - do not run for extended periods!")
    logger.warning("=" * 70)
    
    # Initialize controller
    controller = await initialize_controller(CONTROLLER_ID, TRANSPORT_SETTINGS)
    
    if controller is None:
        logger.error("Failed to connect to controller. Exiting.")
        logger.info("💡 TIP: Run 'python moteus_discover.py' to find your controller!")
        return
    
    try:
        # Lock motor with maximum holding force
        await hold_with_current_timed(
            controller=controller,
            holding_current=HOLDING_CURRENT,
            duration=DURATION,
            update_rate_hz=UPDATE_RATE
        )
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        
    finally:
        # Ensure motor is stopped
        try:
            await controller.set_stop()
        except:
            pass
        
        logger.info("Program complete")


if __name__ == "__main__":
    asyncio.run(main())
