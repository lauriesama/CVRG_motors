#!/usr/bin/env python3
"""
Moteus Motor Test Script - HIGH VOLTAGE HOLD TEST
Test motor holding at 10V, 15V, and 20V for 5 seconds each.

⚠️ WARNING: High voltage testing mode
- Tests at 10V, 15V, and 20V
- 5 second duration per test
- Motor WILL get hot
- Monitor temperature continuously
"""

import moteus
import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_connection(controller: moteus.Controller) -> bool:
    """Test if we can connect to the controller."""
    try:
        logger.info("Testing connection...")
        result = await controller.query()
        if result:
            logger.info(f"✅ Connected! Got response from controller")
            return True
        else:
            logger.error("❌ No response from controller")
            return False
    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
        return False


async def voltage_hold_test(
    controller: moteus.Controller,
    voltage: float,
    duration: float
) -> None:
    """
    Test holding with specific fixed voltage for a duration.
    
    Args:
        controller: moteus controller instance
        voltage: holding voltage in volts (higher = stronger hold)
        duration: how long to hold in seconds
    """
    logger.info("=" * 60)
    logger.info(f"TEST: {voltage}V for {duration} seconds")
    logger.info("👋 KEEP YOUR HAND ON THE MOTOR - try to turn it")
    logger.info("=" * 60)
    
    # Countdown
    for i in range(3, 0, -1):
        logger.info(f"Starting in {i}...")
        await asyncio.sleep(1)
    
    logger.info(f"🔒 LOCKING at {voltage}V!")
    
    loop = asyncio.get_event_loop()
    start_time = loop.time()
    end_time = start_time + duration
    
    try:
        # Use position mode with fixed voltage override
        # Position is set to NaN (don't care about position)
        # fixed_voltage_override applies the voltage
        while loop.time() < end_time:
            await controller.set_position(
                position=float('nan'),  # Don't care about position
                fixed_voltage_override=voltage,
                query=False
            )
            await asyncio.sleep(0.02)  # 50Hz update rate
        
        logger.info("✅ Test complete!")
        
    except Exception as e:
        logger.error(f"❌ Error during test: {e}")
    
    finally:
        # Always stop
        await controller.set_stop()
        logger.info("Motor stopped")
    
    # Cool down pause
    logger.info("💤 Waiting 3 seconds for cool down...")
    await asyncio.sleep(3)


async def main():
    """Run through progressive voltage tests."""
    
    print("""
╔══════════════════════════════════════════════════════════════════╗
║        MOTEUS HIGH VOLTAGE HOLD TEST SEQUENCE                    ║
╚══════════════════════════════════════════════════════════════════╝

⚠️⚠️⚠️ HIGH VOLTAGE TESTING MODE ⚠️⚠️⚠️

This will test your motor at 10V, 15V, and 20V for 5 seconds each.

How it works:
- Uses fixed_voltage_override mode
- Higher voltage = stronger holding force
- WILL generate significant heat at these voltages!

CRITICAL SAFETY RULES:
- Keep your hand on the motor at ALL times
- If motor gets too hot to touch comfortably, press Ctrl+C IMMEDIATELY
- Wait between tests for motor to cool down
- These are SHORT duration tests - NOT for continuous operation!

Ready? Let's push this motor!
""")
    
    # Configuration
    CONTROLLER_ID = 3  # Update this to your controller ID!
    
    # Transport settings
    TRANSPORT_SETTINGS = None  # Auto-detect
    
    print(f"\nController ID: {CONTROLLER_ID}")
    print(f"Transport: {TRANSPORT_SETTINGS if TRANSPORT_SETTINGS else 'Auto-detect'}\n")
    
    input("Press ENTER to start...")
    
    # Initialize controller
    try:
        if TRANSPORT_SETTINGS:
            transport = moteus.Transport(**TRANSPORT_SETTINGS)
            controller = moteus.Controller(id=CONTROLLER_ID, transport=transport)
        else:
            controller = moteus.Controller(id=CONTROLLER_ID)
    except Exception as e:
        logger.error(f"Failed to create controller: {e}")
        print("\n💡 TIP: Run 'python moteus_discover.py' to find your controller!")
        return
    
    # Test connection
    if not await test_connection(controller):
        logger.error("Connection test failed. Check your wiring and controller ID.")
        return
    
    await asyncio.sleep(1)
    
    # Test 1: 10V for 5 seconds
    print("\n" + "=" * 60)
    print("TEST 1: High voltage hold (10V)")
    print("⚠️ Strong holding force. Will generate heat.")
    print("KEEP YOUR HAND ON THE MOTOR to monitor temperature!")
    print("=" * 60)
    input("Press ENTER to continue...")
    await voltage_hold_test(controller, voltage=10.0, duration=5.0)
    
    # Test 2: 15V for 5 seconds  
    print("\n" + "=" * 60)
    print("TEST 2: VERY HIGH voltage hold (15V)")
    print("⚠️⚠️ Very strong holding force. SIGNIFICANT heat generation.")
    print("Motor will get HOT - monitor continuously!")
    print("=" * 60)
    user_input = input("Press ENTER to continue (or 'q' to quit)...")
    if user_input.lower() == 'q':
        logger.info("Test sequence stopped by user")
        return
    await voltage_hold_test(controller, voltage=15.0, duration=5.0)
    
    # Test 3: 20V for 5 seconds
    print("\n" + "=" * 60)
    print("TEST 3: EXTREME voltage hold (20V)")
    print("🔥🔥 EXTREME holding force. Motor will get VERY HOT!")
    print("🔥🔥 STOP IMMEDIATELY if motor is too hot to touch!")
    print("=" * 60)
    user_input = input("Press ENTER to continue (or 'q' to quit)...")
    if user_input.lower() == 'q':
        logger.info("Test sequence stopped by user")
        return
    await voltage_hold_test(controller, voltage=20.0, duration=5.0)
    
    # Complete!
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                     ALL TESTS COMPLETE! 🎉                        ║
╚══════════════════════════════════════════════════════════════════╝

You just pushed your GL60 motor with high voltages!

Results:
- 10V: Strong holding force
- 15V: Very strong holding force  
- 20V: Extreme holding force

⚠️ IMPORTANT NOTES:
- These voltages generate significant heat
- Only use for SHORT durations (5-10 seconds max)
- For continuous holding, stay under 10V
- Always monitor motor temperature

If you want to go even higher (up to 40V), you can manually edit
the test voltages in this script. Just remember:
- Higher voltage = MORE heat
- Keep durations SHORT
- Motor can handle brief peaks but will overheat if sustained

Your motor handled it like a champ! 💪
""")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 Test stopped by user (Ctrl+C)")
        print("Motor should be stopped. If not, power cycle your controller.")