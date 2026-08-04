from config import *


print("GNSS-IR Soil Moisture System")
print("============================")


print("\nProject Directory:")
print(BASE_DIR)


print("\nRINEX Directory:")
print(RINEX_DIR)


print("\nGPS L1 wavelength:")
print(L1_WAVELENGTH, "metres")


print("\nElevation Range:")
print(
    MIN_ELEVATION,
    "-",
    MAX_ELEVATION,
    "degrees"
)


print("\nReflector Height Range:")
print(
    MIN_REFLECTOR_HEIGHT,
    "-",
    MAX_REFLECTOR_HEIGHT,
    "metres"
)