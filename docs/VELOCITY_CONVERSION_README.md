# Ballistics Velocity Conversion - Quick Reference

## Conversion Information

**From:** Feet per Second (fps)  
**To:** Centimeters per Millisecond (cm/ms)

### Conversion Formula

```
1 foot = 30.48 centimeters
1 second = 1000 milliseconds

Therefore:
1 fps = 30.48 cm / 1000 ms = 0.03048 cm/ms
```

Or simply: **fps × 0.03048 = cm/ms**

## Files Generated

1. **velocity_converted_cm_ms.txt** - Summary table with gun names and muzzle velocities
2. **velocity_detailed_cm_ms.txt** - Detailed data showing velocity at different ranges (muzzle, 100yd, 200yd, etc.)

## Statistics (Muzzle Velocities)

- **Total Cartridges:** 250
- **FPS Range:** 1,020 - 4,450 fps
- **CM/MS Range:** 31.09 - 135.64 cm/ms
- **Average Velocity:** 2,777 fps (84.63 cm/ms)

## Sample Conversions

| Gun / Cartridge | FPS | CM/MS |
|----------------|-----|-------|
| 204 Ruger 24 gr. NTX® (fastest) | 4,450 | 135.64 |
| 22-250 Rem 35 gr. NTX® | 4,450 | 135.64 |
| 204 Ruger 32 gr. V-MAX® | 4,225 | 128.78 |
| 223 Rem 35 gr. NTX® | 4,000 | 121.92 |
| 50 BMG 750 gr. A-MAX® | 2,815 | 85.78 |
| 300 Blackout 208 gr. A-MAX® (slowest) | 1,020 | 31.09 |

## Understanding the Units

### What does cm/ms mean?
- **Centimeters per millisecond** measures how many centimeters the bullet travels in one millisecond (1/1000th of a second)
- Example: **135.64 cm/ms** means the bullet travels 135.64 centimeters (about 4.45 feet) in just 1 millisecond

### Comparison
- **Fastest bullet (4,450 fps / 135.64 cm/ms):**
  - Travels 135.64 cm in 1 millisecond
  - Travels 1,356.4 meters in 1 second
  - That's about 3,043 mph or Mach 4.0!

- **Slowest subsonic (1,020 fps / 31.09 cm/ms):**
  - Travels 31.09 cm in 1 millisecond  
  - Travels 310.9 meters in 1 second
  - That's about 695 mph or Mach 0.9

## Usage

Run the parser:
```bash
python3 velocity_parser_enhanced.py
```

Or with custom files:
```bash
python3 velocity_parser_enhanced.py input_file.txt output_file.txt
```

## Data Source
Original data from open source ballistics PDF showing rifle ammunition specifications.
