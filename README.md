# Samsung EHS Home Assistant Integration

> **⚠️ Stability Note**
>
> This integration is stable and ready for use. However, it may not cover all Samsung EHS device models and configurations. Some features or device compatibility may vary depending on your specific setup.
>
> **Technology Readiness Level**: TRL 7 (System prototype demonstration in operational environment)

## Overview

The Samsung EHS integration brings control and monitoring of Samsung Environmental Heat System (EHS) devices to Home Assistant. This integration communicates with Samsung heat pump and heat recovery ventilation systems over the local network using the NASА protocol.

## Why does this exist?

I wanted a local-only solution without relying on Samsung's commercial modbus adapter or their cloud-based WiFi kit (which requires internet connectivity for monitoring and control).

While there are excellent existing projects in this space that have paved the way, I created this integration to address my specific requirements and use case:

- **Samsung HVAC AC component for ESPHome** - This project has done fantastic work and much of the protocol understanding comes from their efforts. For my setup, I needed more flexibility in discovering and monitoring custom registers, and wanted to avoid dedicating the UART connection exclusively to one component. Over extended periods, I also observed some challenges with packet processing in my environment.

- **Samsung EHS -> MQTT** - Another solid project that works well for many users. I wanted a solution that integrated more tightly with Home Assistant's native entities and didn't require running a separate add-on or dedicated device. I also needed support for asynchronous communication patterns to address the message processing problems.

This integration takes a different architectural approach that suited my needs. All of these solutions have contributed valuable knowledge to the community.

## Features

This integration provides support for the following Samsung EHS platforms:

- **Climate** - Monitor and control the heating/cooling mode, target temperature, and HVAC operation status
- **Water Heater** - Manage the domestic hot water (DHW) system with multiple operation modes (Eco, Heat Pump, Electric, Performance)
- **Sensor** - Track various system parameters including temperatures, energy consumption, and operational status
- **Binary Sensor** - Monitor connectivity and device availability
- **Switch** - Control operational features like Quiet Mode and DHW Disinfection
- **Number** - Adjust configuration parameters like DHW disinfection schedule and compressor settings
- **Select** - Choose from predefined options like DHW disinfection day of week and pump modes

## Water Heater Operation Modes

The Samsung EHS water heater (DHW) system supports the following operation modes:

| Home Assistant Mode | Samsung EHS Mode | Description |
|---|---|---|
| Off | Off | Water heater is disabled |
| Eco | ECO | Energy-efficient mode, minimal energy consumption |
| Heat Pump | STANDARD | Standard heat pump operation for water heating |
| Performance | POWER | High-performance mode for faster heating |
| Electric | FORCE | Electric heating element mode for maximum power |

You can switch between these modes in Home Assistant's climate card or through automations. The integration will send the corresponding command to your Samsung EHS device.

## Heating/Cooling Modes

The Samsung EHS climate system supports the following HVAC modes:

| Home Assistant Mode | Samsung EHS Mode | Description |
|---|---|---|
| Off | Off | HVAC system is disabled |
| Auto | AUTO | Uses water law to achieve the set room temperature |
| Heat | HEAT | Heating mode only, if no external thermostats are used, this will control the water flow target temperature |
| Cool | COOL | Cooling mode only, if no external thermostats are used, this will control the water flow target temperature |
| Fan Only | FAN | Fan operation without heating or cooling |

You can change the HVAC mode and set target temperatures through Home Assistant's climate card or automations. The integration will send the corresponding command to your Samsung EHS device.

## HVAC Actions

In addition to HVAC modes, the integration reports the current **HVAC action** - what the system is actually doing at any given moment. This is different from the HVAC mode (what you've set it to do) and is useful for automations and status monitoring.

### HVAC Action States

| Action | Description | Conditions |
|---|---|---|
| **Off** | System is powered off | Power switch is off |
| **Heating** | System is actively heating | Mode is Heat AND outdoor unit running normally |
| **Cooling** | System is actively cooling | Mode is Cool AND outdoor unit running normally |
| **Idle** | System is on but not heating/cooling | Power is on, but no active heating/cooling demand |
| **Preheating** | System is in safety/preheat mode | Outdoor unit in safety operation (OP_SAFETY) |
| **Defrosting** | System is defrosting | Defrost cycle is active on outdoor or indoor unit |

### How HVAC Actions Work

The integration monitors several parameters to determine the current action:

- **Power State**: Whether the system is powered on or off
- **HVAC Mode**: The currently selected mode (Heat, Cool, Fan, Auto)
- **Outdoor Unit Status**: Monitors if the outdoor heat pump unit is running normally (OP_NORMAL), in safety mode (OP_SAFETY), or stopped
- **Defrost Status**: Detects when the system is in defrost cycle to prevent ice buildup

**Example Scenarios**:

- **Heating without demand**: HVAC mode is Heat, system is on, but room temperature is at target → Action shows "Idle"
- **Heating with defrost**: System needs to heat but defrost cycle is active → Action shows "Defrosting"
- **System shutdown**: Power is off → Action shows "Off" regardless of mode setting
- **Cold startup**: System starting up and warming before normal operation → Action shows "Preheating"

This information is exposed as the `hvac_action` attribute in Home Assistant and can be used in automations to trigger actions based on what the system is actually doing, not just what mode it's in.

## Services

This integration provides the following services for advanced control and monitoring:

### Read Attribute

Read an attribute value from your Samsung EHS device.

**Service**: `samsungehs.read_attribute`

**Fields**:
- `device_id` (required): The Samsung EHS device to read from
- `attribute` (required): The attribute ID in format `0xXXXX` (e.g., `0x0001`)

**Example**:
```yaml
service: samsungehs.read_attribute
data:
   device_id: abc123def456
   attribute: "0x0001"
```

**Attribute IDs**: See the [pysamsungnasa message factory documentation](https://pantherale0.github.io/pysamsungnasa/protocol/message-factory/) for available attribute IDs.

### Write Attribute

Write a value to an attribute on your Samsung EHS device.

**Service**: `samsungehs.write_attribute`

**Fields**:
- `device_id` (required): The Samsung EHS device to write to
- `attribute` (required): The attribute ID in format `0xXXXX` (e.g., `0x0001`)
- `value` (required): The value to write

**Example**:
```yaml
service: samsungehs.write_attribute
data:
   device_id: abc123def456
   attribute: "0x0001"
   value: 42
```

**Attribute IDs**: See the [pysamsungnasa message factory documentation](https://pantherale0.github.io/pysamsungnasa/protocol/message-factory/) for available attribute IDs and their expected value formats.

## Hardware Configuration

Samsung EHS devices communicate via the NASА protocol over RS485/serial connection. Since most systems won't have direct serial access, you'll need to set up a UART bridge to connect your Home Assistant instance to the Samsung EHS device.

### Required Hardware

To establish communication, you will need:

1. **A device with RS485 interface** - Examples:
    - M5Stack with [RS485 Base](https://www.aliexpress.com/item/1005005912210853.html)
    - Any ESP32-based device with RS485 module
    - Raspberry Pi with RS485 HAT

2. **Network connectivity** - The bridge device must be on the same network as Home Assistant

### Setting Up with ESPHome

The recommended approach is to use [ESPHome](https://esphome.io/) with the [esphome-stream-server](https://github.com/oxan/esphome-stream-server) component:

1. **Flash ESPHome to your bridge device** (e.g., M5Stack):
    - Install [ESPHome](https://esphome.io/guides/installing_esphome.html)
    - Create a new device configuration with RS485 support
    - Use the esphome-stream-server component for TCP bridging

2. **Example ESPHome Configuration**:
    ```yaml
    esphome:
       name: samsung-ehs-bridge

    uart:
       id: uart_rs485
       tx_pin: GPIO17
       rx_pin: GPIO16
       baud_rate: 9600

    external_components:
       - source: github://oxan/esphome-stream-server

    stream_server:
       uart_id: uart_rs485
       port: 8000
    ```

3. **Connect the RS485 module**:
    - Wire the RS485 module to your ESP device according to your specific hardware pinout
    - Connect the RS485 A/B lines to your Samsung EHS device
    - Ensure proper termination resistors if needed for your installation

4. **Note the device's IP address** - This will be used in the Home Assistant configuration

### Connecting to Samsung EHS Device

⚠️ **SAFETY WARNING**: The Samsung EHS heatpump contains high voltages. Ensure the unit is electrically isolated from power supply before making any electrical connections.

**Connection Points**:

The RS485 communication lines connect to the **F1 and F2 terminals** on your Samsung EHS unit. These can be found on either:

- **Indoor Unit**: Control board or communication module
- **Outdoor Unit**: Main control board

**Wiring**:

- RS485 **A** line → F1 terminal
- RS485 **B** line → F2 terminal
- Ensure a common ground connection between the bridge and the heatpump unit

**Power Supply**:

The M5Stack ESP32 device can be powered independently via USB, or you can use the **12V power terminals** on the Samsung EHS unit when using the M5Stack RS485 Base:

- **12V +** terminal → M5Stack RS485 Base 12V input
- **12V -** (ground) → Common ground with the heatpump

This option eliminates the need for separate external power and keeps all connections in one location.

**Important Safety Steps**:

1. **Turn off the heatpump** at the main power switch before connecting any cables
2. **Verify the unit is de-energized** using a multimeter if possible
3. **Use insulated terminals** when connecting to F1/F2 to prevent accidental contact
4. **Check your specific unit's manual** for exact terminal locations (they may vary by model)
5. **Power on the unit only after all connections are verified** and the bridge device is powered on

### Network Connection

Once your UART bridge is set up:
- Your Samsung EHS device communicates via RS485 to the bridge hardware
- The bridge converts this to TCP/IP and exposes it on port 8000
- Home Assistant connects to the bridge via your local network

## Installation

### Via Home Assistant Community Store (HACS)

1. Add this repository to HACS as a custom repository
2. Search for "Samsung EHS" in HACS
3. Click Install
4. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/samsungehs` directory to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Go to Settings → Devices & Services → Create Integration
4. Search for "Samsung EHS" and follow the configuration flow

## Configuration

### Via UI

The integration uses the configuration flow for easy setup:

1. Go to Settings → Devices & Services → Create Integration
2. Search for "Samsung EHS"
3. Enter the following information:
    - **Host**: The IP address or hostname of your RS485 bridge / ethernet adapter
    - **Port**: The port number to access the bridge

The integration will automatically discover and set up all connected devices and their entities.

## Supported Devices

This integration supports Samsung EHS systems that communicate via the NASА protocol, including:

- Samsung heat pumps (ASHP, WSHP models)
- Samsung air-to-water heat pumps
- Samsung heat recovery ventilation systems with integrated heat pump functionality
- This integration may support a variety of Samsung AC units, however as I don't have any packet dumps from these, I cannot implmenent the required functions.

**Note**: Compatibility depends on your specific device model and firmware version. Please refer to the [issue tracker](https://github.com/pantherale0/ha-samsungehs/issues) if you encounter compatibility issues.

## How It Works

The integration uses the `pysamsungnasa` library to communicate with Samsung EHS devices over a local network connection. It:

1. Establishes a TCP connection to the EHS device
2. Continuously polls the device for status updates (every 15 seconds by default)
3. Translates device-specific protocols into Home Assistant entities
4. Provides climate control, water heater management, and sensor monitoring capabilities

All communication is local and does not require internet connectivity.

## Troubleshooting

### Device Not Found

- Ensure your device is connected to the same network as Home Assistant
- Verify the IP address and port number are correct
- Check that your device's firewall allows connections on the configured port

### Connection Issues

- Restart the integration from Settings → Devices & Services
- Check the Home Assistant logs for error messages
- Ensure your device is powered on and responsive

### Missing Entities

Some entities may not appear if your device firmware doesn't support them. This is normal behavior.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this project.

## Development

This project includes a development environment that can be set up using Docker and Visual Studio Code:

```bash
# Lint the code
./scripts/lint

# Set up development environment
./scripts/setup

# Start development environment
./scripts/develop
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Support

For issues, feature requests, or questions, please use the [GitHub issue tracker](https://github.com/pantherale0/ha-samsungehs/issues).

## Related Projects

- [pysamsungnasa](https://github.com/pantherale0/pysamsungnasa) - Python library for Samsung NASА protocol
- [Home Assistant](https://www.home-assistant.io/) - Open-source home automation platform