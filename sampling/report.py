# Copyright 2025 Kulikov Artem

import subprocess
import pathlib


def parse_maps(maps_lines):
    mappings = {}
    for line in maps_lines:
        parts = line.split()
        if len(parts) < 6:
            continue
        address_range = parts[0]
        # permissions = parts[1]
        offset = parts[2]
        # device = parts[3]
        # inode = parts[4]
        pathname = " ".join(parts[5:])
        start, end = address_range.split("-")
        mappings[pathname] = {
            "start": int(start, 16),
            "end": int(end, 16),
            "offset": int(offset, 16),
            "addresses": set(),
        }
    return mappings


def main():
    with open("mpt.map", "r") as file:
        lines = file.readlines()

    maps_lines = [line.strip() for line in lines if "r-xp" in line and "/" in line]
    mappings = parse_maps(maps_lines)

    with open("mpt.txt", "r") as file:
        lines = file.readlines()

    address_lines = [line.strip() for line in lines]

    for line in address_lines:
        for addr in line.split():
            address = int(addr, 16)
            for mapping in mappings.values():
                if mapping["start"] <= address <= mapping["end"]:
                    mapping["addresses"].add(address)
                    break

    text = "\n".join(address_lines)

    for pathname, mapping in mappings.items():
        if not mapping["addresses"]:
            continue

        start, offset = mapping["start"], mapping["offset"]
        address_orig = list(mapping["addresses"])
        addresses = map(lambda address: hex(address - start + offset), address_orig)

        try:
            # TODO(me): implement addr2line logic
            result = subprocess.check_output(
                ["addr2line", "-e", pathname, "-f", "-C", *addresses],
                stderr=subprocess.STDOUT,
            )
            data = result.decode("utf-8").strip().splitlines()
            binary = pathlib.Path(pathname).name
            for i in range(len(data) // 2):
                repl = f"{data[i * 2]}({binary})"
                text = text.replace(hex(address_orig[i]), repl)
        except subprocess.CalledProcessError:
            continue

    lines = text.splitlines()
    n = len(lines)

    not_call_stack = True
    for line in lines:
        if ' ' in line:
            not_call_stack = False
            break

    if not_call_stack:
        # regular output
        from collections import Counter

        ds = sorted(dict(Counter(lines)).items(), key=lambda kv: kv[1], reverse=True)
        for k, v in ds:
            print(f"{v/n:5.2f}", k)
    else:
        # flamegraph format
        ds = {}
        for line in lines:
            if line in ds:
                ds[line] += 1
            else:
                ds[line] = 1  # call order
        ds = ds.items()

        for k, v in ds:
            print(";".join(reversed(k.split(" "))), v)


if __name__ == "__main__":
    main()
