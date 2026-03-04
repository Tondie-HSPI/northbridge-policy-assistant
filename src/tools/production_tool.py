def calculate_production_capacity(rate_per_hour, hours_available):
    """
    Calculate total production capacity.
    """
    capacity = rate_per_hour * hours_available
    return capacity


def estimate_effective_output(capacity, defect_rate):
    """
    Estimate usable production output after accounting for defect rate.
    """
    usable_output = capacity * (1 - defect_rate)
    return usable_output