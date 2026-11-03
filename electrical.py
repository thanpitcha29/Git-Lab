from math import isfinite


def analyze_dc(voltage_v, resistance_ohm):
    for name, value in (("voltage_v", voltage_v), ("resistance_ohm", resistance_ohm)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{name} must be a number")
        try:
            finite = isfinite(value)
        except OverflowError:
            finite = False
        if not finite:
            raise ValueError(f"{name} must be finite")
    if resistance_ohm <= 0:
        raise ValueError("resistance_ohm must be greater than zero")

    try:
        current_a = voltage_v / resistance_ohm
        power_w = voltage_v * current_a
    except OverflowError:
        raise ValueError("calculation result is outside the supported numeric range") from None
    if not isfinite(current_a) or not isfinite(power_w):
        raise ValueError("calculation result is outside the supported numeric range")

    return {"current_a": current_a, "power_w": power_w}


def main():
    try:
        voltage_v = float(input("Voltage (V): "))
        resistance_ohm = float(input("Resistance (ohm): "))
        result = analyze_dc(voltage_v, resistance_ohm)
    except ValueError as error:
        print(f"Invalid input: {error}")
        return 1

    print(f"Current: {result['current_a']:.2f} A")
    print(f"Power: {result['power_w']:.2f} W")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())