import os
import json
import subprocess
import re


def resolve_addresses_to_symbols(binary_path):
    nm_output = subprocess.check_output(["nm", "-C", binary_path], text=True)
    symbol_map = {}
    main_addr = None
    for line in nm_output.splitlines():
        match = re.match(r"([0-9a-fA-F]+)\s+[Tt]\s+(\S+)", line)
        if match:
            addr, symbol = match.groups()
            symbol_map[int(addr, 16)] = symbol
            if not main_addr and symbol == "main":
                main_addr = int(addr, 16)
    return symbol_map, main_addr


def parse_data_file_TRACE(lines: list[str], symbol_map, main_addr, binary_path):
    base = lines[0].strip().split()[1]
    offset = int(base, 16) - main_addr

    events = []
    stack = []
    thread_id = 0
    pid = binary_path

    for line in lines:
        parts = line.strip().split()

        cur_time = int(parts[0])
        if len(parts) == 2:  # ->
            addr = parts[1]
            read_addr = int(addr, 16) - offset
            symbol = symbol_map.get(read_addr, addr)

            stack.append(symbol)

            events.append(
                {
                    "name": symbol,
                    "ph": "B",
                    "ts": cur_time / 1000,  # ns to mсs
                    "pid": pid,
                    "tid": thread_id,
                    "args": {},
                }
            )

        else:  # <-
            symbol = stack.pop()

            events.append(
                {
                    "name": symbol,
                    "ph": "E",
                    "ts": cur_time / 1000,  # ns to mсs
                    "pid": pid,
                    "tid": thread_id,
                    "args": {},
                }
            )

    return events


def main():
    data_file = "out.iprof"
    if not os.path.isfile(data_file):
        data_file = input("Please input path to trace (out.iprof): ").strip()

    with open(data_file, "r") as f:
        lines = f.readlines()

    binary_path = lines.pop(0).strip()
    if not binary_path:
        binary_path = input("Please input path to instrumented binary: ").strip()

    symbol_map, main_addr = resolve_addresses_to_symbols(binary_path)

    prof_tp = lines.pop(0).strip()
    if prof_tp == "TRACE":
        trace_events = parse_data_file_TRACE(lines, symbol_map, main_addr, binary_path)
    else:
        print(f"Unsupported profile type: {prof_tp}")
        return

    trace_data = {
        "traceEvents": trace_events,
        "displayTimeUnit": "ns",
    }

    with open("trace.json", "w") as f:
        json.dump(trace_data, f, indent=2)

    print("Trace file generated: trace.json")


if __name__ == "__main__":
    main()
