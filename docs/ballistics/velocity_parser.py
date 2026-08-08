#!/usr/bin/env python3
"""
Ballistics Velocity Parser
Converts velocity measurements from feet per second (fps) to millimeters per second (mm/s)

Conversion factor: 1 foot = 304.8 millimeters
"""

def fps_to_mms(fps):
    """
    Convert feet per second to millimeters per second
    
    Args:
        fps (float): Velocity in feet per second
    
    Returns:
        float: Velocity in millimeters per second
    """
    return fps * 304.8


def parse_velocity_file(input_file, output_file=None):
    """
    Parse velocity data file and convert all fps values to mm/s
    
    Args:
        input_file (str): Path to input file with fps values
        output_file (str): Optional path to output file. If None, prints to console
    
    Returns:
        list: List of tuples containing (fps, mm/s) pairs
    """
    results = []
    
    with open(input_file, 'r') as f:
        lines = f.readlines()
    
    # Skip header lines
    data_start = False
    for line in lines:
        line = line.strip()
        
        # Skip empty lines and header
        if not line or not data_start:
            if any(char.isdigit() for char in line):
                data_start = True
            else:
                continue
        
        # Parse comma-separated velocity values
        if ',' in line:
            velocities = [v.strip() for v in line.split(',') if v.strip()]
            for vel_str in velocities:
                try:
                    fps = float(vel_str)
                    mms = fps_to_mms(fps)
                    results.append((fps, mms))
                except ValueError:
                    continue
    
    # Output results
    if output_file:
        with open(output_file, 'w') as f:
            f.write("Velocity Conversion: Feet per Second (fps) to Millimeters per Second (mm/s)\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"{'FPS':>10} | {'MM/S':>15} | {'Meters/Second':>15}\n")
            f.write("-" * 80 + "\n")
            
            for fps, mms in results:
                meters_per_sec = mms / 1000
                f.write(f"{fps:>10.1f} | {mms:>15.1f} | {meters_per_sec:>15.2f}\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"Total values converted: {len(results)}\n")
    else:
        print("Velocity Conversion: Feet per Second (fps) to Millimeters per Second (mm/s)")
        print("=" * 80)
        print(f"{'FPS':>10} | {'MM/S':>15} | {'Meters/Second':>15}")
        print("-" * 80)
        
        for fps, mms in results[:20]:  # Show first 20 for console
            meters_per_sec = mms / 1000
            print(f"{fps:>10.1f} | {mms:>15.1f} | {meters_per_sec:>15.2f}")
        
        if len(results) > 20:
            print(f"... ({len(results) - 20} more values)")
        
        print("\n" + "=" * 80)
        print(f"Total values converted: {len(results)}")
    
    return results


def get_statistics(velocities):
    """
    Calculate statistics for velocity data
    
    Args:
        velocities (list): List of (fps, mm/s) tuples
    
    Returns:
        dict: Statistics including min, max, average
    """
    if not velocities:
        return {}
    
    fps_values = [v[0] for v in velocities]
    mms_values = [v[1] for v in velocities]
    
    return {
        'fps': {
            'min': min(fps_values),
            'max': max(fps_values),
            'avg': sum(fps_values) / len(fps_values)
        },
        'mm/s': {
            'min': min(mms_values),
            'max': max(mms_values),
            'avg': sum(mms_values) / len(mms_values)
        },
        'count': len(velocities)
    }


if __name__ == "__main__":
    import sys
    import os
    
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(script_dir, "velocity_data.txt")
    output_file = os.path.join(script_dir, "velocity_converted.txt")
    
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
    
    print(f"Reading velocity data from: {input_file}")
    print(f"Writing converted data to: {output_file}")
    print()
    
    # Parse and convert
    results = parse_velocity_file(input_file, output_file)
    
    # Display statistics
    stats = get_statistics(results)
    print("\nStatistics:")
    print("-" * 40)
    print(f"Total values: {stats['count']}")
    print(f"\nFPS - Min: {stats['fps']['min']:.1f}, Max: {stats['fps']['max']:.1f}, Avg: {stats['fps']['avg']:.1f}")
    print(f"MM/S - Min: {stats['mm/s']['min']:.1f}, Max: {stats['mm/s']['max']:.1f}, Avg: {stats['mm/s']['avg']:.1f}")
    print(f"M/S - Min: {stats['mm/s']['min']/1000:.2f}, Max: {stats['mm/s']['max']/1000:.2f}, Avg: {stats['mm/s']['avg']/1000:.2f}")
    
    print(f"\n✓ Conversion complete! Output saved to: {output_file}")
