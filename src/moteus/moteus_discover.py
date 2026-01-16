#!/usr/bin/env python3
"""
Moteus Device Discovery Script
Helps you find your moteus controller and figure out the correct connection settings.
"""

import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_connection_with_settings(controller_id: int, transport_settings: dict) -> bool:
    """
    Test connection with specific settings.
    
    Args:
        controller_id: Controller ID to try
        transport_settings: Dictionary of transport settings
        
    Returns:
        True if connection successful
    """
    import moteus
    
    try:
        logger.info(f"Trying ID {controller_id} with settings: {transport_settings}")
        
        # Create controller with specific transport
        if transport_settings:
            transport = moteus.Transport(**transport_settings)
            controller = moteus.Controller(id=controller_id, transport=transport)
        else:
            controller = moteus.Controller(id=controller_id)
        
        # Try to query with a timeout
        result = await asyncio.wait_for(controller.query(), timeout=2.0)
        
        if result:
            logger.info(f"✅ SUCCESS! Found controller at ID {controller_id}")
            logger.info(f"   Mode: {result.mode}")
            logger.info(f"   Settings: {transport_settings if transport_settings else 'default'}")
            return True
        else:
            logger.debug(f"   No response from ID {controller_id}")
            return False
            
    except asyncio.TimeoutError:
        logger.debug(f"   Timeout on ID {controller_id}")
        return False
    except Exception as e:
        logger.debug(f"   Error on ID {controller_id}: {e}")
        return False


async def scan_for_controllers():
    """Scan for moteus controllers with different configurations."""
    
    print("""
╔══════════════════════════════════════════════════════════════════╗
║              MOTEUS CONTROLLER DISCOVERY TOOL                    ║
╚══════════════════════════════════════════════════════════════════╝

This will try to find your moteus controller by testing:
- Common controller IDs (1-10)
- Different CAN interfaces
- USB connections

This may take a minute...
""")
    
    found_controllers = []
    
    # Test configurations to try
    test_configs = [
        # Default - no explicit transport (tries to auto-detect)
        {"name": "Default (auto-detect)", "settings": None},
        
        # Explicit USB serial
        {"name": "USB Serial (auto-detect port)", "settings": {}},
        
        # Common serial ports
        {"name": "USB /dev/ttyACM0", "settings": {"serial_port": "/dev/ttyACM0"}},
        {"name": "USB /dev/ttyUSB0", "settings": {"serial_port": "/dev/ttyUSB0"}},
        
        # CAN interfaces
        {"name": "CAN socketcan", "settings": {"type": "socketcan", "interface": "can0"}},
        {"name": "CAN slcan", "settings": {"type": "slcan", "interface": "/dev/ttyACM0"}},
    ]
    
    # IDs to scan (most people use 1-4, but let's check up to 10)
    controller_ids = range(1, 11)
    
    logger.info("Starting scan...")
    
    for config in test_configs:
        print(f"\n{'='*60}")
        print(f"Testing: {config['name']}")
        print('='*60)
        
        for controller_id in controller_ids:
            try:
                success = await test_connection_with_settings(controller_id, config['settings'])
                if success:
                    found_controllers.append({
                        "id": controller_id,
                        "config_name": config['name'],
                        "settings": config['settings']
                    })
            except KeyboardInterrupt:
                logger.info("Scan interrupted by user")
                return found_controllers
            except Exception as e:
                logger.debug(f"Unexpected error: {e}")
                continue
    
    return found_controllers


def generate_code_snippet(controller_info):
    """Generate Python code snippet for the found controller."""
    
    settings = controller_info['settings']
    controller_id = controller_info['id']
    
    if settings is None:
        # Default transport
        return f"""
# Default transport (auto-detect)
controller = moteus.Controller(id={controller_id})
"""
    elif not settings:
        # Empty dict means USB with auto-detect
        return f"""
# USB with auto-detect port
transport = moteus.Transport()
controller = moteus.Controller(id={controller_id}, transport=transport)
"""
    elif 'serial_port' in settings:
        # Explicit serial port
        return f"""
# USB with explicit port
transport = moteus.Transport(serial_port="{settings['serial_port']}")
controller = moteus.Controller(id={controller_id}, transport=transport)
"""
    else:
        # CAN or other
        settings_str = ", ".join([f'{k}="{v}"' for k, v in settings.items()])
        return f"""
# Custom transport settings
transport = moteus.Transport({settings_str})
controller = moteus.Controller(id={controller_id}, transport=transport)
"""


async def main():
    """Main discovery routine."""
    
    try:
        import moteus
    except ImportError:
        print("""
❌ ERROR: moteus library not found!

Install it with:
    pip install moteus

Then run this script again.
""")
        return
    
    # Check for serial ports
    try:
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())
        if ports:
            print("\n📌 Available serial ports detected:")
            for port in ports:
                print(f"   - {port.device}: {port.description}")
        else:
            print("\n⚠️  No serial ports detected!")
    except ImportError:
        print("\n⚠️  pyserial not installed (optional)")
    
    print("\nStarting controller scan...\n")
    
    # Scan for controllers
    found = await scan_for_controllers()
    
    # Print results
    print("\n" + "="*60)
    print("SCAN COMPLETE")
    print("="*60)
    
    if not found:
        print("""
❌ No controllers found!

Troubleshooting steps:
1. Is your moteus controller powered on?
2. Is it connected via USB or CAN?
3. For USB: Check if /dev/ttyACM0 or /dev/ttyUSB0 exists
4. For CAN: Is your CAN interface configured? (try 'ip link show can0')
5. Try manually setting the controller ID if you changed it

If using USB, try running:
    ls -la /dev/ttyACM* /dev/ttyUSB*

If using CAN, try running:
    ip link show
""")
    else:
        print(f"\n✅ Found {len(found)} controller(s)!\n")
        
        for i, ctrl in enumerate(found, 1):
            print(f"Controller #{i}:")
            print(f"  ID: {ctrl['id']}")
            print(f"  Connection: {ctrl['config_name']}")
            print(f"\n  Code to use:")
            print(generate_code_snippet(ctrl))
            print()
    
    return found


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 Scan stopped by user (Ctrl+C)")
