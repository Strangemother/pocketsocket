#!/usr/bin/env python3
"""
Ballistics Velocity Parser (Enhanced)
Converts velocity measurements from feet per second (fps) to centimeters per millisecond (cm/ms)

Conversion:
1 foot = 30.48 centimeters
1 second = 1000 milliseconds
Therefore: 1 fps = 30.48 cm / 1000 ms = 0.03048 cm/ms
"""

import re

def fps_to_cm_per_ms(fps):
    """
    Convert feet per second to centimeters per millisecond
    
    Args:
        fps (float): Velocity in feet per second
    
    Returns:
        float: Velocity in centimeters per millisecond
    """
    # 1 foot = 30.48 cm, 1 second = 1000 ms
    # So 1 fps = 30.48/1000 = 0.03048 cm/ms
    return fps * 0.03048


def parse_ballistics_data(input_file):
    """
    Parse the ballistics file and extract gun names with velocities
    
    Args:
        input_file (str): Path to ballistics data file
    
    Returns:
        list: List of dicts with gun info and velocities
    """
    results = []
    
    with open(input_file, 'r') as f:
        lines = f.readlines()
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines and headers
        if not line or line.startswith('Rifle') or line.startswith('Ammo') or line.startswith('CARTRIDGE'):
            continue
        if line.startswith('All data from'):
            continue
        if line.startswith('Ballistics'):
            continue
            
        # Match lines that start with cartridge codes (letters followed by space)
        # Pattern: Code CARTRIDGE_NAME BULLET_SPEC ITEM# velocities...
        match = re.match(r'^([A-Z]+)\s+(.+?)\s+(\d+(?:\.\d+)?)\s+gr\.\s+(.+?)\s+(\d+)\s+([\d\s—]+)', line)
        
        if match:
            code = match.group(1)
            cartridge = match.group(2).strip()
            grain = match.group(3)
            bullet_type = match.group(4).strip()
            item_num = match.group(5)
            velocity_str = match.group(6)
            
            # Extract numeric velocities
            velocities = []
            for vel in velocity_str.split():
                if vel == '—':
                    continue
                try:
                    v = float(vel)
                    if v > 500:  # Filter out energy/trajectory values
                        velocities.append(v)
                except ValueError:
                    break
            
            if velocities and len(velocities) >= 3:
                # Take only the first velocity value (muzzle velocity)
                muzzle_velocity = velocities[0]
                
                gun_name = f"{cartridge} {grain} gr. {bullet_type}"
                
                results.append({
                    'code': code,
                    'gun_name': gun_name,
                    'cartridge': cartridge,
                    'grain': grain,
                    'bullet': bullet_type,
                    'item': item_num,
                    'fps': muzzle_velocity,
                    'cm_ms': fps_to_cm_per_ms(muzzle_velocity),
                    'all_velocities': velocities
                })
    
    return results


def write_output(data, output_file):
    """
    Write formatted output to file
    
    Args:
        data (list): List of gun data dictionaries
        output_file (str): Path to output file
    """
    with open(output_file, 'w') as f:
        f.write("=" * 100 + "\n")
        f.write("BALLISTICS VELOCITY CONVERSION\n")
        f.write("Feet per Second (fps) → Centimeters per Millisecond (cm/ms)\n")
        f.write("=" * 100 + "\n\n")
        
        f.write(f"{'GUN / CARTRIDGE':<60} {'FPS':>10} | {'CM/MS':>10}\n")
        f.write("-" * 100 + "\n")
        
        for item in data:
            gun_display = item['gun_name'][:58]  # Truncate if too long
            f.write(f"{gun_display:<60} {item['fps']:>10.0f} | {item['cm_ms']:>10.4f}\n")
        
        f.write("\n" + "=" * 100 + "\n")
        f.write(f"Total entries: {len(data)}\n")
        f.write("\nConversion Factor: 1 fps = 0.03048 cm/ms\n")
        f.write("(1 foot = 30.48 cm, 1 second = 1000 milliseconds)\n")


def write_detailed_output(data, output_file):
    """
    Write detailed output with all velocity measurements
    
    Args:
        data (list): List of gun data dictionaries
        output_file (str): Path to output file
    """
    with open(output_file, 'w') as f:
        f.write("=" * 120 + "\n")
        f.write("DETAILED BALLISTICS VELOCITY CONVERSION\n")
        f.write("Muzzle Velocity & Range Data: Feet per Second (fps) → Centimeters per Millisecond (cm/ms)\n")
        f.write("=" * 120 + "\n\n")
        
        for item in data:
            f.write(f"\n{item['gun_name']}\n")
            f.write(f"Item: {item['item']} | Cartridge: {item['cartridge']}\n")
            f.write("-" * 80 + "\n")
            
            # Display velocities at different ranges
            ranges = ['Muzzle', '100 yd', '200 yd', '300 yd', '400 yd', '500 yd']
            f.write(f"{'Range':<12} | {'FPS':>10} | {'CM/MS':>10}\n")
            f.write("-" * 40 + "\n")
            
            for i, vel in enumerate(item['all_velocities'][:6]):
                range_name = ranges[i] if i < len(ranges) else f"{i}00+ yd"
                cm_ms = fps_to_cm_per_ms(vel)
                f.write(f"{range_name:<12} | {vel:>10.0f} | {cm_ms:>10.4f}\n")
            
            f.write("\n")
        
        f.write("=" * 120 + "\n")
        f.write(f"Total entries: {len(data)}\n")
        f.write("\nConversion Factor: 1 fps = 0.03048 cm/ms\n")


def get_statistics(data):
    """
    Calculate statistics for velocity data
    
    Args:
        data (list): List of gun data dictionaries
    
    Returns:
        dict: Statistics
    """
    if not data:
        return {}
    
    fps_values = [item['fps'] for item in data]
    cm_ms_values = [item['cm_ms'] for item in data]
    
    return {
        'fps': {
            'min': min(fps_values),
            'max': max(fps_values),
            'avg': sum(fps_values) / len(fps_values)
        },
        'cm/ms': {
            'min': min(cm_ms_values),
            'max': max(cm_ms_values),
            'avg': sum(cm_ms_values) / len(cm_ms_values)
        },
        'count': len(data)
    }


if __name__ == "__main__":
    import sys
    import os
    
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(script_dir, "ballastics-speeds.txt")
    output_file = os.path.join(script_dir, "velocity_converted_cm_ms.txt")
    detailed_file = os.path.join(script_dir, "velocity_detailed_cm_ms.txt")
    
    # Check if custom input file provided
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found!")
        print(f"\nUsage: {sys.argv[0]} [input_file] [output_file]")
        sys.exit(1)
    
    print(f"Reading ballistics data from: {input_file}")
    print(f"Writing summary to: {output_file}")
    print(f"Writing detailed data to: {detailed_file}")
    print()
    
    # Parse and convert
    data = parse_ballistics_data(input_file)
    
    if not data:
        print("Error: No data could be parsed from the input file!")
        sys.exit(1)
    
    # Write outputs
    write_output(data, output_file)
    write_detailed_output(data, detailed_file)
    
    # Display statistics
    stats = get_statistics(data)
    print("\nStatistics (Muzzle Velocities):")
    print("-" * 60)
    print(f"Total cartridges: {stats['count']}")
    print(f"\nFPS    - Min: {stats['fps']['min']:.0f}, Max: {stats['fps']['max']:.0f}, Avg: {stats['fps']['avg']:.0f}")
    print(f"CM/MS  - Min: {stats['cm/ms']['min']:.4f}, Max: {stats['cm/ms']['max']:.4f}, Avg: {stats['cm/ms']['avg']:.4f}")
    
    print(f"\n✓ Conversion complete!")
    print(f"  - Summary: {output_file}")
    print(f"  - Detailed: {detailed_file}")
    
    # Show sample
    print(f"\nSample conversions:")
    print("-" * 60)
    for item in data[:5]:
        print(f"{item['gun_name'][:50]:<50}")
        print(f"  {item['fps']:.0f} fps = {item['cm_ms']:.4f} cm/ms")
