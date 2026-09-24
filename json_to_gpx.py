#!/usr/bin/env python3

import argparse
import json
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

"""    
Takes a processed GPS json file, and outputs it as .gpx file for easily displaying the route of the recording.
"""

# GPX Namespace
GPX_NS = "http://www.topografix.com/GPX/1/1"

"""Convert a numeric ASCII value such as 77 into 'N'."""
def ascii_to_char(value):
    try:
        return chr(int(value))
    except (ValueError, TypeError):
        return str(value)


"""Converts degrees + minutes into decimal degrees."""
def convert_coordinate(degrees, minutes, hemisphere):
    coordinate = float(degrees) + float(minutes) / 60.0
    return coordinate


"""Convert Unix timestamp to ISO-8601 UTC timestamp."""
def timestamp_to_iso(timestamp):
    dt = datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def parse_json(input_file):
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(
            "Expected the JSON file to contain a top-level list of records."
        )

    return data

"""
    Extract GPS points from the CAN signal records.

    Signals are accumulated by timestamp. Once latitude, longitude,
    and optionally altitude are available, a track point is created.
"""
def extract_gps_points(data):
    # Group signals by timestamp.
    # Using the timestamp as a key is sufficient for our data,
    # where related GPS signals have essentially identical timestamps.
    samples = {}

    for entry in data:
        timestamp = float(entry.get("timestamp", 0))
        signal = entry.get("signal")
        value = entry.get("value")

        if signal is None:
            continue

        if timestamp not in samples:
            samples[timestamp] = {}

        samples[timestamp][signal] = value

    points = []

    # Sort chronologically
    for timestamp in sorted(samples):
        signals = samples[timestamp]

        # Latitude
        lat_degree = signals.get("GPS_Latitude_Degree")
        lat_minutes = signals.get("GPS_Latitude_Minutes")
        lat_indicator = signals.get("GPS_IndicatorNS")

        # Longitude
        lon_degree = signals.get("GPS_Longitude_Degree")
        lon_minutes = signals.get("GPS_Longitude_Minutes")
        lon_indicator = signals.get("GPS_IndicatorEW")

        # Altitude
        altitude = signals.get("GPS_Altitude")

        # We need a complete coordinate pair
        if (
            lat_degree is None
            or lat_minutes is None
            or lat_indicator is None
            or lon_degree is None
            or lon_minutes is None
            or lon_indicator is None
        ):
            continue

        try:
            latitude = convert_coordinate(
                lat_degree,
                lat_minutes,
                lat_indicator,
            )

            longitude = convert_coordinate(
                lon_degree,
                lon_minutes,
                lon_indicator,
            )

            altitude = float(altitude) if altitude is not None else None

            points.append({
                "timestamp": timestamp,
                "latitude": latitude,
                "longitude": longitude,
                "altitude": altitude,
            })

        except (ValueError, TypeError):
            continue

    return points


"""Create a GPX 1.1 file containing a single route."""
def create_gpx(points, output_file):
    ET.register_namespace("", GPX_NS)

    gpx = ET.Element(
        f"{{{GPX_NS}}}gpx",
        {
            "version": "1.1",
            "creator": "M3S/AIC Json to Gpx",
        },
    )

    trk = ET.SubElement(gpx, f"{{{GPX_NS}}}trk")

    name = ET.SubElement(trk, f"{{{GPX_NS}}}name")
    name.text = "Vehicle GPS Route"

    trkseg = ET.SubElement(trk, f"{{{GPX_NS}}}trkseg")

    for point in points:
        trkpt = ET.SubElement(
            trkseg,
            f"{{{GPX_NS}}}trkpt",
            {
                "lat": f"{point['latitude']:.8f}",
                "lon": f"{point['longitude']:.8f}",
            },
        )

        if point["altitude"] is not None:
            ele = ET.SubElement(trkpt, f"{{{GPX_NS}}}ele")
            ele.text = f"{point['altitude']:.3f}"

        time = ET.SubElement(trkpt, f"{{{GPX_NS}}}time")
        time.text = timestamp_to_iso(point["timestamp"])

    tree = ET.ElementTree(gpx)

    # Pretty-print if available
    try:
        ET.indent(tree, space="  ")
    except AttributeError:
        pass

    tree.write(
        output_file,
        encoding="utf-8",
        xml_declaration=True,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Convert vehicle CAN GPS JSON data to GPX."
    )

    parser.add_argument(
        "input",
        help="Input JSON file",
    )

    parser.add_argument(
        "output",
        help="Output GPX file",
    )

    args = parser.parse_args()

    print(f"Reading: {args.input}")

    data = parse_json(args.input)

    print(f"Loaded {len(data):,} CAN signal records")

    points = extract_gps_points(data)

    print(f"Extracted {len(pointsh:,} GPS points")

    if not points:
        raise RuntimeError(
            "No complete GPS points could be extracted. "
            "Check the signal names in the JSON."
        )

    create_gpx(points, args.output)

    print(f"GPX written to: {args.output}")

    print()
    print("First point:")
    print(f"  Latitude:  {points[0]['latitude']:.8f}")
    print(f"  Longitude: {points[0]['longitude']:.8f}")
    print(f"  Altitude:  {points[0]['altitude']}")
    print()
    print("Last point:")
    print(f"  Latitude:  {points[-1]['latitude']:.8f}")
    print(f"  Longitude: {points[-1]['longitude']:.8f}")
    print(f"  Altitude:  {points[-1]['altitude']}")


if __name__ == "__main__":
    main()
