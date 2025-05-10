# AIOv2 - GPS Location Overlay

## Overview

`aiov2.py` is an All-In-One (AIO) application that displays real-time GPS location data as a floating overlay on your desktop. It combines a Flask server to receive location updates with a PyQt5-based graphical interface to display location information with an elegant map visualization.

## Features

- **Real-time GPS tracking**: Receives and processes location data via a local Flask server
- **Elegant map visualization**: Displays a satellite map centered on the current location
- **Reverse geocoding**: Shows the address of the current location using Nominatim geocoding
- **Always-on-top overlay**: Floating window that stays on top of other applications
- **System tray integration**: Minimizes to system tray for easy access
- **Customizable interface**: Toggle between fixed and movable window modes

## Components

1. **Flask Server** 
   - Listens on port 5000 for location updates
   - Endpoints:
     - `/log`: Receives and logs location data (POST/GET)
     - `/location`: Returns the latest logged location (GET)

2. **PyQt5 Overlay**
   - Displays current location on a satellite map
   - Shows address, coordinates, date, and time
   - Provides controls to hide or edit the overlay

## Requirements

- Python 3.6+
- Flask
- PyQt5
- geopy
- Pillow (PIL)
- requests

## Usage

1. Run the script directly:
   ```
   python aiov2.py
   ```

2. Send location data to the server using HTTP requests to:
   ```
   http://localhost:5000/log?lat=<latitude>&lon=<longitude>
   ```

3. The overlay will automatically update when new location data is received.
