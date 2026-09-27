#!/usr/bin/env python3
"""
Ballistics Speed Micro Examples
Comparing slowest, average, and fastest bullet velocities in various units
"""

def fps_to_all_units(fps):
    """
    Convert fps to all requested units
    
    Args:
        fps (float): Feet per second
    
    Returns:
        dict: All conversions
    """
    # Base conversions
    feet_per_sec = fps
    meters_per_sec = fps * 0.3048  # 1 foot = 0.3048 meters
    cm_per_sec = fps * 30.48       # 1 foot = 30.48 cm
    mm_per_sec = fps * 304.8       # 1 foot = 304.8 mm
    mm_per_microsec = fps * 0.0003048  # 1 fps = 304.8 mm/s = 0.0003048 mm/μs
    
    return {
        'fps': feet_per_sec,
        'm/s': meters_per_sec,
        'cm/s': cm_per_sec,
        'mm/s': mm_per_sec,
        'mm/μs': mm_per_microsec
    }


def main():
    # Based on the actual ballistics data
    slowest_fps = 1020
    average_fps = 2777
    fastest_fps = 4450
    
    slowest_name = "300 Blackout 208 gr. A-MAX®"
    average_name = "Average across all 250 cartridges"
    fastest_name = "204 Ruger 24 gr. NTX® / 22-250 Rem 35 gr. NTX®"
    
    print("=" * 100)
    print("BALLISTICS SPEED MICRO EXAMPLES")
    print("Comparing Slowest, Average, and Fastest Bullet Velocities")
    print("=" * 100)
    print()
    
    # Process each category
    categories = [
        ("SLOWEST", slowest_fps, slowest_name),
        ("AVERAGE", average_fps, average_name),
        ("FASTEST", fastest_fps, fastest_name)
    ]
    
    for category, fps_value, gun_name in categories:
        conversions = fps_to_all_units(fps_value)
        
        print(f"\n{'─' * 100}")
        print(f"{category}: {gun_name}")
        print(f"{'─' * 100}")
        print(f"  Feet per Second (fps)         : {conversions['fps']:>12,.2f} fps")
        print(f"  Meters per Second (m/s)       : {conversions['m/s']:>12,.2f} m/s")
        print(f"  Centimeters per Second (cm/s) : {conversions['cm/s']:>12,.2f} cm/s")
        print(f"  Millimeters per Second (mm/s) : {conversions['mm/s']:>12,.2f} mm/s")
        print(f"  Millimeters per Microsecond   : {conversions['mm/μs']:>12,.6f} mm/μs")
        print()
        
        # Add some context
        print(f"  Context:")
        print(f"    • Travels {conversions['m/s']:.2f} meters in 1 second")
        print(f"    • Travels {conversions['mm/μs']:.6f} millimeters in 1 microsecond (1/1,000,000 second)")
        print(f"    • Speed of sound ≈ 343 m/s, this is Mach {conversions['m/s']/343:.2f}")
        
        # Travel distance examples
        travel_1ms = conversions['mm/s'] / 1000
        travel_1us = conversions['mm/μs']
        travel_1ns = conversions['mm/μs'] / 1000
        
        print(f"\n  Distance traveled:")
        print(f"    • In 1 millisecond  (0.001 s)  : {travel_1ms:>10.2f} mm  ({travel_1ms/10:.2f} cm)")
        print(f"    • In 1 microsecond  (0.000001 s): {travel_1us:>10.6f} mm  ({travel_1us*1000:.3f} μm)")
        print(f"    • In 1 nanosecond   (0.000000001 s): {travel_1ns:>10.9f} mm  ({travel_1ns*1000:.6f} μm)")
    
    print()
    print("=" * 100)
    print("SUMMARY TABLE")
    print("=" * 100)
    print()
    print(f"{'Category':<10} | {'FPS':>10} | {'M/S':>10} | {'CM/S':>12} | {'MM/S':>12} | {'MM/μS':>12}")
    print("─" * 100)
    
    for category, fps_value, _ in categories:
        conv = fps_to_all_units(fps_value)
        print(f"{category:<10} | {conv['fps']:>10,.0f} | {conv['m/s']:>10,.2f} | "
              f"{conv['cm/s']:>12,.2f} | {conv['mm/s']:>12,.2f} | {conv['mm/μs']:>12.6f}")
    
    print()
    print("=" * 100)
    print("\nNOTES:")
    print("  • 1 foot = 0.3048 meters = 30.48 centimeters = 304.8 millimeters")
    print("  • 1 second = 1,000 milliseconds = 1,000,000 microseconds = 1,000,000,000 nanoseconds")
    print("  • Speed of sound at sea level ≈ 343 m/s (1,125 fps)")
    print("  • All velocities shown are muzzle velocities (at the barrel exit)")
    print()


if __name__ == "__main__":
    main()
