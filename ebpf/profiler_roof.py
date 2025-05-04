# Copyright 2025 Kulikov Artem

from bcc import BPF, utils

code = """
#include <uapi/linux/ptrace.h>

struct perf_delta {
    u64 clk_delta;
    u64 inst_delta;
    u64 time_delta;
    u64 chrf_delta;
    u64 chms_delta;
    u64 flops_delta;
};

BPF_PERF_ARRAY(clk, MAX_CPUS);
BPF_PERF_ARRAY(inst, MAX_CPUS);
BPF_PERF_ARRAY(chrf, MAX_CPUS);
BPF_PERF_ARRAY(chms, MAX_CPUS);

BPF_PERF_ARRAY(flops, MAX_CPUS);

BPF_PERCPU_ARRAY(data, u64);

BPF_PERF_OUTPUT(output);

#define CLOCK_ID 0
#define INSTRUCTION_ID 1
#define TIME_ID 2
#define CACHE_REF_ID 3
#define CACHE_MSS_ID 4

#define FLOPS_ID 5

void trace_start(struct pt_regs *ctx) {
    u32 clk_k = CLOCK_ID;
    u32 inst_k = INSTRUCTION_ID;
    u32 time = TIME_ID;
    u32 chrf_k = CACHE_REF_ID;
    u32 chms_k = CACHE_MSS_ID;
    u32 flops_k = FLOPS_ID;
    int cpu = bpf_get_smp_processor_id();

    u64 clk_start = clk.perf_read(cpu);
    u64 inst_start = inst.perf_read(cpu);
    u64 time_start = bpf_ktime_get_ns();
    u64 chrf_start = chrf.perf_read(cpu);
    u64 chms_start = chms.perf_read(cpu);

    u64 flops_start = flops.perf_read(cpu);
    
    u64* kptr = NULL;
    kptr = data.lookup(&clk_k);
    if (kptr) data.update(&clk_k, &clk_start);
    else data.insert(&clk_k, &clk_start);
    
    kptr = data.lookup(&inst_k);
    if (kptr) data.update(&inst_k, &inst_start);
    else data.insert(&inst_k, &inst_start);

    kptr = data.lookup(&time);
    if (kptr) data.update(&time, &time_start);
    else data.insert(&time, &time_start);

    kptr = data.lookup(&chrf_k);
    if (kptr) data.update(&chrf_k, &chrf_start);
    else data.insert(&chrf_k, &chrf_start);

    kptr = data.lookup(&chms_k);
    if (kptr) data.update(&chms_k, &chms_start);
    else data.insert(&chms_k, &chms_start);

    kptr = data.lookup(&flops_k);
    if (kptr) data.update(&flops_k, &flops_start);
    else data.insert(&flops_k, &flops_start);
}
void trace_end(struct pt_regs* ctx) {
    u32 clk_k = CLOCK_ID;
    u32 inst_k = INSTRUCTION_ID;
    u32 time = TIME_ID;
    u32 chrf_k = CACHE_REF_ID;
    u32 chms_k = CACHE_MSS_ID;
    u32 flops_k = FLOPS_ID;
    int cpu = bpf_get_smp_processor_id();

    u64 clk_end = clk.perf_read(cpu);
    u64 inst_end = inst.perf_read(cpu);
    u64 time_end = bpf_ktime_get_ns();
    u64 chrf_end = chrf.perf_read(cpu);
    u64 chms_end = chms.perf_read(cpu);

    u64 flops_end = flops.perf_read(cpu);
    
    struct perf_delta perf_data;
    u64* kptr = NULL;

    kptr = data.lookup(&clk_k);
    if (!kptr) return;
    perf_data.clk_delta = clk_end - *kptr;
    
    kptr = data.lookup(&inst_k);
    if (!kptr) return;
    perf_data.inst_delta = inst_end - *kptr;
    
    kptr = data.lookup(&time);
    if (!kptr) return;
    perf_data.time_delta = time_end - *kptr;

    kptr = data.lookup(&chrf_k);
    if (!kptr) return;
    perf_data.chrf_delta = chrf_end - *kptr;

    kptr = data.lookup(&chms_k);
    if (!kptr) return;
    perf_data.chms_delta = chms_end - *kptr;

    kptr = data.lookup(&flops_k);
    if (!kptr) return;
    perf_data.flops_delta = flops_end - *kptr;
    
    output.perf_submit(ctx, &perf_data, sizeof(struct perf_delta));
}
"""

b = BPF(text=code, cflags=["-DMAX_CPUS=%s" % str(len(utils.get_online_cpus()))])

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

b.attach_uprobe(name=name, sym_re=sym, fn_name="trace_start")
b.attach_uretprobe(name=name, sym_re=sym, fn_name="trace_end")

# 3.10GHz; 
# /proc/cpuinfo:
# cpu MHz		: 2569.502

# dmidecode --type 17
# Speed: 1600 MT/s

# 1600 * 1e6 * 64 / 8 = 12800000000 b/s

# https://www.intel.com/content/www/us/en/content-details/841556/app-metrics-for-intel-microprocessors-intel-core-processor.html
# Processor Number GFLOPS (Gigaflops) APP (Adjusted Peak Performance)
# i5-3340 99.2 0.02976



def print_data(cpu, data, size):
    e = b["output"].event(data)
    print(
        "%-16d %-16d %-4.2f %-16s %-4d %-16d %-16d %-16.6f %-16.6f"
        % (
            e.clk_delta,
            e.inst_delta,
            1.0 * e.inst_delta / e.clk_delta,
            str(round(e.time_delta * 1e-3, 2)) + " us",
            cpu,
            e.chrf_delta,
            e.chms_delta,
            1.0 * e.chms_delta / e.chrf_delta,
            1.0 * e.chms_delta / e.clk_delta,
        )
    )

    P_peak = 99.2 * (2 ** 30) # FLOP/s
    M = 1600 * 1e6 * 64 / 8 # BYTE/s

    BYTES = e.chms_delta * 64
    SECS = e.time_delta * 1e-9
    I = e.flops_delta / BYTES
    P = e.flops_delta / SECS

    print(f'{I=}, {(P_peak/M)=}')


print("Counters Data")
print(
    "%-16s %-16s %-4s %-16s %-4s %-16s %-16s %-16s %-16s"
    % (
        "CLOCK",
        "INSTRUCTION",
        "IPC",
        "TIME",
        "CPU",
        "CACHE REF",
        "CACHE MISS",
        "CACHE MISS/all",
        "CACHE MISS/sec",
    )
)

b["output"].open_perf_buffer(print_data)

from bcc import PerfType, PerfHWConfig


b["clk"].open_perf_event(PerfType.HARDWARE, PerfHWConfig.CPU_CYCLES) # not PERF_COUNT_HW_REF_CPU_CYCLES
b["inst"].open_perf_event(PerfType.HARDWARE, PerfHWConfig.INSTRUCTIONS)
b["chrf"].open_perf_event(PerfType.HARDWARE, PerfHWConfig.CACHE_REFERENCES)
# b["chms"].open_perf_event(PerfType.HARDWARE, PerfHWConfig.CACHE_MISSES)

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

b["chms"].open_perf_event(PerfType.HW_CACHE, 
                        #   PERF_COUNT_HW_CACHE_DTLB | 
                          PERF_COUNT_HW_CACHE_L1D | 
                          (PERF_COUNT_HW_CACHE_OP_READ << 8) |
                          (PERF_COUNT_HW_CACHE_RESULT_MISS << 16))


# Intel Volume 3B documentation
FP_COMP_OPS_EXE_SSE_PACKED_SINGLE = 0x4010
FP_COMP_OPS_EXE_SSE_SCALAR_SINGLE = 0x2010
b["flops"].open_perf_event(PerfType.RAW, FP_COMP_OPS_EXE_SSE_SCALAR_SINGLE)


while True:
    try:
        b.perf_buffer_poll()
    except KeyboardInterrupt:
        exit()
