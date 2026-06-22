def humanize(value):
    units = ("B", "KiB", "MiB", "GiB")
    number = float(value or 0)
    index = 0
    while number >= 1024 and index < len(units) - 1:
        number /= 1024
        index += 1
    return f"{number:.1f}{units[index]}" if index else f"{int(number)}{units[index]}"
