# Copyright 2025 Kulikov Artem

from bcc import BPF, utils

code = """
#include <uapi/linux/ptrace.h>

struct perf_delta {{
    u64 time_start;
    u64 time_end;
{struct_fields}
}};

{perf_arrays}

BPF_PERCPU_ARRAY(data, u64);

BPF_PERF_OUTPUT(output);

#define TIME_ID 0
{arr_keys}

void trace_start(struct pt_regs *ctx) {{
    u32 time = TIME_ID;
{init_keys}

    int cpu = bpf_get_smp_processor_id();

    u64 time_start = bpf_ktime_get_ns();
{collect_perf}
    
    u64* kptr = NULL;

    kptr = data.lookup(&time);
    if (kptr) data.update(&time, &time_start);
    else data.insert(&time, &time_start);

{insert_perf}
}}
void trace_end(struct pt_regs* ctx) {{
    u32 time = TIME_ID;

{init_keys}

    int cpu = bpf_get_smp_processor_id();

    u64 time_end = bpf_ktime_get_ns();
{collect_perf_end}

    struct perf_delta perf_data;
    u64* kptr = NULL;

    kptr = data.lookup(&time);
    if (!kptr) return;
    perf_data.time_start = *kptr;
    perf_data.time_end = time_end;

{prepare_data}

    output.perf_submit(ctx, &perf_data, sizeof(struct perf_delta));
}}
"""


def get_fmt_dict(names: list[str]):
    perf_arrays = '\n'.join([f'BPF_PERF_ARRAY({name}, MAX_CPUS);' for name in names])
    struct_fields = '\n'.join([f'    u64 {name}_delta;' for name in names])
    arr_keys = '\n'.join([f'#define {name.upper()}_ID {i}' for i, name in enumerate(names, 1)])
    init_keys = '\n'.join([f'    u32 {name}_k = {name.upper()}_ID;' for name in names])
    collect_perf = '\n'.join([f'    u64 {name}_start = {name}.perf_read(cpu);' for name in names])
    insert_perf = '\n'.join([f'    kptr = data.lookup(&{name}_k);\n    if (kptr) data.update(&{name}_k, &{name}_start);\n    else data.insert(&{name}_k, &{name}_start);\n' for name in names])
    collect_perf_end = '\n'.join([f'    u64 {name}_end = {name}.perf_read(cpu);' for name in names])
    prepare_data = '\n'.join([f'    kptr = data.lookup(&{name}_k);\n    if (!kptr) return;\n    perf_data.{name}_delta = {name}_end - *kptr;\n' for name in names])

    return {
        'perf_arrays': perf_arrays, 'struct_fields': struct_fields, 'arr_keys': arr_keys, 
        'init_keys': init_keys, 
        'collect_perf': collect_perf, 'insert_perf': insert_perf, 
        'collect_perf_end': collect_perf_end, 'prepare_data': prepare_data
    }


name = "./a.out"
sym = "*"

import sys

argv = sys.argv[1:]
argc = len(argv)
print(argc, argv)

if argc:
    name = argv[0]
    argc -= 1
if argc:
    sym = argv[1]

from bcc import PerfType, PerfHWConfig

# /usr/include/linux/perf_event.h
PERF_COUNT_HW_CACHE_L1D			= 0
PERF_COUNT_HW_CACHE_L1I			= 1
PERF_COUNT_HW_CACHE_LL			= 2
PERF_COUNT_HW_CACHE_DTLB		= 3
PERF_COUNT_HW_CACHE_ITLB		= 4
PERF_COUNT_HW_CACHE_BPU			= 5
PERF_COUNT_HW_CACHE_NODE		= 6

PERF_COUNT_HW_CACHE_OP_READ		    = 0
PERF_COUNT_HW_CACHE_OP_WRITE		= 1
PERF_COUNT_HW_CACHE_OP_PREFETCH		= 2

PERF_COUNT_HW_CACHE_RESULT_ACCESS	= 0
PERF_COUNT_HW_CACHE_RESULT_MISS		= 1

a_ = PERF_COUNT_HW_CACHE_RESULT_ACCESS<<16|PERF_COUNT_HW_CACHE_OP_READ<<8|PERF_COUNT_HW_CACHE_LL
b_ = PERF_COUNT_HW_CACHE_RESULT_ACCESS<<16|PERF_COUNT_HW_CACHE_OP_PREFETCH<<8|PERF_COUNT_HW_CACHE_LL
c_ = PERF_COUNT_HW_CACHE_RESULT_ACCESS<<16|PERF_COUNT_HW_CACHE_OP_WRITE<<8|PERF_COUNT_HW_CACHE_LL
d_ = PERF_COUNT_HW_CACHE_RESULT_MISS<<16|PERF_COUNT_HW_CACHE_OP_READ<<8|PERF_COUNT_HW_CACHE_L1D
e_ = PERF_COUNT_HW_CACHE_RESULT_ACCESS<<16|PERF_COUNT_HW_CACHE_OP_READ<<8|PERF_COUNT_HW_CACHE_L1D
f_ = PERF_COUNT_HW_CACHE_RESULT_ACCESS<<16|PERF_COUNT_HW_CACHE_OP_WRITE<<8|PERF_COUNT_HW_CACHE_L1D


MEM_UOPS_RETIRED_ALL_LOADS = 0xD0 | 0x81 << 8
MEM_LOAD_UOPS_RETIRED_LLC_MISS = 0xD1 | 0x20 << 8

    # 'chrf': (PerfType.HARDWARE, PerfHWConfig.CACHE_REFERENCES),
    # 'chms': (PerfType.HARDWARE, PerfHWConfig.CACHE_MISSES),
    # 'ch_ld_m_l1_x': (PerfType.HW_CACHE, d_),

# Should Bytes be 
# amount of processed bytes = algorithm characteristic
# or number of bytes read from DDR = which is actually the bottleneck

FP_COMP_OPS_EXE_SSE_SCALAR_SINGLE = 0x10 | 0x20 << 8
FP_COMP_OPS_EXE_SSE_PACKED_SINGLE = 0x10 | 0x40 << 8
SIMD_FP_256_PACKED_SINGLE = 0x11 | 0x01 << 8

names = {
    "instrs" : (PerfType.HARDWARE, PerfHWConfig.INSTRUCTIONS),
    'mem_rd': (PerfType.HW_CACHE, e_), # same as (PerfType.RAW, MEM_UOPS_RETIRED_ALL_LOADS)
    'mem_wr': (PerfType.HW_CACHE, f_),
    'flop_ss': (PerfType.RAW, FP_COMP_OPS_EXE_SSE_SCALAR_SINGLE),
    'flop_ps': (PerfType.RAW, FP_COMP_OPS_EXE_SSE_PACKED_SINGLE),
    'simd_ps': (PerfType.RAW, SIMD_FP_256_PACKED_SINGLE),
}

# if delta < D(tot_ops) => d = 0
# Let D(tot_ops) be Tot*0.001



# from https://github.com/icl-utk-edu/papi/blob/master/src/papi_events.csv
# IvyBridge
# Counts scalars only; no SSE or AVX is counted; includes speculative
# PRESET,PAPI_FP_INS,DERIVED_ADD,FP_COMP_OPS_EXE:SSE_SCALAR_DOUBLE,FP_COMP_OPS_EXE:SSE_FP_SCALAR_SINGLE,FP_COMP_OPS_EXE:X87
# PRESET,PAPI_FP_OPS,DERIVED_ADD,FP_COMP_OPS_EXE:SSE_SCALAR_DOUBLE,FP_COMP_OPS_EXE:SSE_FP_SCALAR_SINGLE,FP_COMP_OPS_EXE:X87
#
# PRESET,PAPI_SP_OPS,DERIVED_POSTFIX,N0|N1|4|*|N2|8|*|+|+|,FP_COMP_OPS_EXE:SSE_FP_SCALAR_SINGLE,FP_COMP_OPS_EXE:SSE_PACKED_SINGLE,SIMD_FP_256:PACKED_SINGLE
# PRESET,PAPI_DP_OPS,DERIVED_POSTFIX,N0|N1|2|*|N2|4|*|+|+|,FP_COMP_OPS_EXE:SSE_SCALAR_DOUBLE,FP_COMP_OPS_EXE:SSE_FP_PACKED_DOUBLE,SIMD_FP_256:PACKED_DOUBLE
# PRESET,PAPI_VEC_SP,DERIVED_POSTFIX,N0|4|*|N1|8|*|+|,FP_COMP_OPS_EXE:SSE_PACKED_SINGLE,SIMD_FP_256:PACKED_SINGLE
# PRESET,PAPI_VEC_DP,DERIVED_POSTFIX,N0|2|*|N1|4|*|+|,FP_COMP_OPS_EXE:SSE_FP_PACKED_DOUBLE,SIMD_FP_256:PACKED_DOUBLE

code = code.format_map(get_fmt_dict(names.keys()))

b = BPF(text=code, cflags=["-DMAX_CPUS=%s" % str(len(utils.get_online_cpus())), "-Wno-macro-redefined"])
b.attach_uprobe(name=name, sym_re=sym, fn_name="trace_start")
b.attach_uretprobe(name=name, sym_re=sym, fn_name="trace_end")

for name, evt in names.items():
    b[name].open_perf_event(*evt)


# Intel Volume 3B documentation
# interesting FP events by Intel family

# Sandy Bridge:
# FP_COMP_OPS_EXE.* (Number of SSE* or AVX-128 FP Computational * uops issued this cycle)

# Ivy Bridge:
# FP_COMP_OPS_EXE.*
# SIMD_FP_256.* (Counts 256-bit packed * floating-point instructions)

# Haswell: ?

# Broadwell:
# Skylake:
# Ice Lake:
# Tiger Lake:
# FP_ARITH_INST_RETIRED.* (Number of SSE/AVX computational *)

# Alder Lake:
# Raptor Lake:
# FP_ARITH_DISPATCHED.* (by port)
# FP_ARITH_INST_RETIRED.*

# ...

# System Params:
# /proc/cpuinfo:
# 3.10GHz; 
# cpu MHz		: 2569.502

# dmidecode --type 17
# Speed: 1600 MT/s

# 1600 * 1e6 * 64 / 8 = 12800000000 b/s

# https://www.intel.com/content/www/us/en/content-details/841556/app-metrics-for-intel-microprocessors-intel-core-processor.html
# Processor Number GFLOPS (Gigaflops) APP (Adjusted Peak Performance)
# i5-3340 99.2 0.02976

# P_peak = n_core * n_super * n_fma * f_flops
P_peak = 1 * 4 * 1 * (3100 * 1e6) # FLOP/s
# 3100 ops - not flops ?
# n_super=4 - from noploop

# M = n_chan * 8b * f_btps
M = 2 * (64 / 8) * (800 * 1e6) # BYTE/s

def print_data(cpu, data, size):
    e = b["output"].event(data)

    time_delta = e.time_end - e.time_start
    BYTES = e.chms_delta * 64 # check another way
    SECS = time_delta * 1e-9
    I = e.flops_delta / BYTES
    P = e.flops_delta / SECS

    print(
        "%-4d %-16d %-16d %-16d %-16d %-16s %-16d"
        % (
            cpu,
            e.inst_delta,
            e.flops_delta,
            e.time_start,
            e.time_end,
            f'{time_delta} ns',
            e.chms_delta,
        )
    )
    # print(f'{I=:.3f}, {(P_peak/M)=:.3f}')


# print("Counters Data")
# print(
#     "%-4s %-16s %-16s %-16s %-16s %-16s %-16s"
#     % (
#         "CPU",
#         "INSTRUCTION",
#         "FLOP",
#         "TIME START",
#         "TIME END",
#         "TIME DELTA",
#         "CACHE MISS",
#     )
# )

def print_generic(cpu, data, size):
    e = b["output"].event(data)

    print("%-16s %d" % ("cpu", cpu))

    time_start = e.time_start
    print("%-16s %d" % ("time_start", time_start))
    time_end = e.time_end
    print("%-16s %d" % ("time_end", time_end))
    time_delta = time_end - time_start
    print("%-16s %d ns" % ("time_delta", time_delta))

    for name in names.keys():
        print("%-16s %d" % (name, getattr(e, f'{name}_delta')))


# b["output"].open_perf_buffer(print_data)
b["output"].open_perf_buffer(print_generic)


while True:
    try:
        b.perf_buffer_poll()
    except KeyboardInterrupt:
        exit()
