import subprocess
import re
from collections import defaultdict
import networkx as nx
from pyvis.network import Network
import pydot


# python -m pip install pyvis
# python -m pip install networkx[default]

# python -m pip install pydot
# python -m pip install graphviz
# sudo apt-get install graphviz


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


def parse_data_file_TRACE(lines: list[str], symbol_map, main_addr):
    base = lines[0].strip().split()[1]
    offset = int(base, 16) - main_addr

    graph = {}
    stack = []
    for line in lines:
        parts = line.strip().split()

        cur_time = int(parts[0])
        if len(parts) == 2:  # ->
            addr = parts[1]
            read_addr = int(addr, 16) - offset
            symbol = symbol_map.get(read_addr, addr)

            stack.append([symbol, cur_time, 0])

            if symbol not in graph:
                graph[symbol] = {"self": 0, "n": 0, "children": {}}

        else:  # <-
            symbol, start_time, child_dur = stack.pop()
            duration = cur_time - start_time
            self_dur = duration - child_dur

            graph[symbol]["n"] += 1
            graph[symbol]["self"] += self_dur

            if stack:
                top = stack[-1]
                top[2] += duration

                children = graph[top[0]]["children"]
                child = children.get(symbol)
                if child:
                    child["n"] += 1
                    child["t"] += duration
                else:
                    children[symbol] = {"n": 1, "t": duration}

    return graph


def parse_data_file_GRAPH(lines: list[str], symbol_map, main_addr):
    base = lines.pop(0).strip()
    offset = int(base, 16) - main_addr

    graph = {}
    parent = None
    for line in lines:
        if parent:
            children_table = graph[parent]["children"]
            chilren = line.strip().split("|")
            for child in chilren:
                if not child:
                    break
                addr, info = child.strip().split(":")
                n, t = info.split(" ")

                read_addr = int(addr, 16) - offset
                symbol = symbol_map.get(read_addr, addr)

                children_table[symbol] = {"n": float(n), "t": float(t)}
            parent = None
        else:
            addr, info = line.strip().split(":")
            n, t = info.split(" ")

            read_addr = int(addr, 16) - offset
            symbol = symbol_map.get(read_addr, addr)

            graph[symbol] = {"self": float(t), "n": float(n), "children": {}}
            parent = symbol

    return graph


import math


# my old red parametric ~ bezier quadratic
def ryg_grad_old(red: float):
    return (red, -(1 - red) + 2 * math.sqrt(1 - red), 0)


def ryg_grad_bezier_cubic(t: float):
    comm = 3 * t * (1 - t)
    return (t**3 + comm, (1 - t) ** 3 + comm, 0)

def frac_func_to_int(func, *args, **kwargs):
    res = func(*args, **kwargs)
    return tuple(map(lambda x: min(max(int(x * 255), 0), 255), res))


def paint_graph(graph_mem, strats, output_file="call_graph"):
    graph = pydot.Dot(graph_type="digraph")
    graph.set_node_defaults(color="lightgray", style="filled")

    for name, data in graph_mem.items():
        irgbs = []
        for target, (reg, avg) in strats.items():
            x_reg = data[target]
            x_avg = x_reg // data["n"]
            badness_reg = reg(x_reg)
            badness_avg = avg(x_avg)
            irgbs.extend([
                frac_func_to_int(ryg_grad_bezier_cubic, badness_reg),
                frac_func_to_int(ryg_grad_bezier_cubic, badness_avg)
            ])

        target = "self"
        x_reg = data["self"]
        x_avg = x_reg //  data["n"]
        label = f"{name}\n{target}: {x_reg}ns" + \
                    (f"\nCount: {data['n']}\nAvg: {x_avg}ns" if data['n'] != 1 else "")

        graph.add_node(pydot.Node(name, label=label,
            style="wedged",
            fillcolor=":".join(
            [f"#{r:02x}{g:02x}{b:02x}" for (r, g, b) in irgbs]
        )))


    legend_node = pydot.Node("legend",
    label=r'''<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">
            <TR><TD WIDTH="30" HEIGHT="30">self avg</TD><TD WIDTH="30" HEIGHT="30">self real</TD></TR>
            <TR><TD WIDTH="30" HEIGHT="30">full real</TD><TD WIDTH="30" HEIGHT="30">full avg</TD></TR>
           </TABLE>>''',
    shape="none")
    graph.add_node(legend_node)

    for name, data in graph_mem.items():
        child_t = sum(child_data["t"] for child_data in data["children"].values())
        n = len(data["children"])
        for child_name, child_data in data["children"].items():
            weight = child_data["t"] / child_t
            title = f'{child_data["n"]}' + (f" ({weight:.2f})" if n != 1 else "")

            graph.add_edge(pydot.Edge(name, child_name, taillabel=title))

    graph.write_png(f"{output_file}.png")


def strat1(val, max_x):
    return val / max_x


def strat2(val, max_x):
    return math.log1p(val / max_x)


def strat3(val, edges, cdf):
    for i in range(len(edges) - 2):
        if val <= edges[i + 1]:
            return float(cdf[i])
    return float(cdf[len(edges) - 2])


def strat5(val, k, qcuts, vals):
    for i in range(k - 1):
        if val < qcuts[i]:
            return vals[i]
    return vals[k - 1]


import numpy as np
import os


def main():
    # TODO:
    # 1. check argv
    # 2. check curdir
    # 3. ask input

    data_file = "out.iprof"
    if not os.path.isfile(data_file):
        data_file = input("Please input path to trace (out.iprof)").strip()

    with open(data_file, "r") as f:
        lines = f.readlines()

    binary_path = lines.pop(0).strip()
    if not binary_path:
        binary_path = input("Please input path to instrmented binary").strip()

    symbol_map, main_addr = resolve_addresses_to_symbols(binary_path)

    prof_tp = lines.pop(0).strip()
    if prof_tp == "TRACE":
        graph_mem = parse_data_file_TRACE(lines, symbol_map, main_addr)
    elif prof_tp == "GRAPH":
        graph_mem = parse_data_file_GRAPH(lines, symbol_map, main_addr)
    else:
        print(f"Unsupported profile type: {prof_tp}")
        return

    # graph_mem = {
    #     "main": {
    #         "self": 61800,
    #         "n": 1,
    #         "children": {"foo": {"n": 1, "t": 400}, "bar": {"n": 2, "t": 2900}},
    #     },
    #     "foo": {"self": 1100, "n": 7, "children": {}},
    #     "bar": {"self": 2200, "n": 2, "children": {"foo": {"n": 6, "t": 700}}},
    # }

    for node_name, data in graph_mem.items():
        data["full"] = data["self"] + sum(
            child_data["t"] for child_data in data["children"].values()
        )

        # handling recursion
        for child_name, child_data in data["children"].items():
            if child_name == node_name:
                data["self"] += child_data["t"]
                break


    n_bins = int(np.pow(len(graph_mem), 1 / 3)) * 3

    k = n_bins
    qs = [i / k for i in range(1, k)]
    vals = [i / (k - 1) for i in range(0, k)]

    qcuts = np.quantile([sym["self"] for sym in graph_mem.values()], qs)
    s51 = lambda val: strat5(val, k, qcuts, vals)

    qcuts = np.quantile([sym["self"] // sym["n"] for sym in graph_mem.values()], qs)
    s52 = lambda val: strat5(val, k, qcuts, vals)

    qcuts = np.quantile([sym["full"] for sym in graph_mem.values()], qs)
    s53 = lambda val: strat5(val, k, qcuts, vals)

    qcuts = np.quantile([sym["full"] // sym["n"] for sym in graph_mem.values()], qs)
    s54 = lambda val: strat5(val, k, qcuts, vals)

    import time
    paint_graph(graph_mem, {
        "self": (s51, s52),
        "full": (s53, s54)
    }, f"graph_{time.time()}")


if __name__ == "__main__":
    main()
