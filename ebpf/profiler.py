from bcc import BPF, utils

code="""
#include <uapi/linux/ptrace.h>

struct perf_delta {
    u64 clk_delta;
    u64 inst_delta;
    u64 time_delta;
    u64 chrf_delta;
    u64 chms_delta;
};

BPF_PERF_ARRAY(clk, MAX_CPUS);
BPF_PERF_ARRAY(inst, MAX_CPUS);
BPF_PERF_ARRAY(chrf, MAX_CPUS);
BPF_PERF_ARRAY(chms, MAX_CPUS);

BPF_PERCPU_ARRAY(data, u64);

BPF_PERF_OUTPUT(output);

#define CLOCK_ID 0
#define INSTRUCTION_ID 1
#define TIME_ID 2
#define CACHE_REF_ID 3
#define CACHE_MSS_ID 4

void trace_start(struct pt_regs *ctx) {
    u32 clk_k = CLOCK_ID;
    u32 inst_k = INSTRUCTION_ID;
    u32 time = TIME_ID;
    u32 chrf_k = CACHE_REF_ID;
    u32 chms_k = CACHE_MSS_ID;
    int cpu = bpf_get_smp_processor_id();

    u64 clk_start = clk.perf_read(cpu);
    u64 inst_start = inst.perf_read(cpu);
    u64 time_start = bpf_ktime_get_ns();
    u64 chrf_start = chrf.perf_read(cpu);
    u64 chms_start = chms.perf_read(cpu);
    
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
}
void trace_end(struct pt_regs* ctx) {
    u32 clk_k = CLOCK_ID;
    u32 inst_k = INSTRUCTION_ID;
    u32 time = TIME_ID;
    u32 chrf_k = CACHE_REF_ID;
    u32 chms_k = CACHE_MSS_ID;
    int cpu = bpf_get_smp_processor_id();

    u64 clk_end = clk.perf_read(cpu);
    u64 inst_end = inst.perf_read(cpu);
    u64 time_end = bpf_ktime_get_ns();
    u64 chrf_end = chrf.perf_read(cpu);
    u64 chms_end = chms.perf_read(cpu);
    
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
    
    output.perf_submit(ctx, &perf_data, sizeof(struct perf_delta));
}
"""

b = BPF(text=code, cflags=['-DMAX_CPUS=%s' % str(len(utils.get_online_cpus()))])

name = "ls"
sym = "main"

import sys
argv = sys.argv
argc = len(argv) - 1
if argc:
    name = argv[0]
    argc -= 1
if argc:
    sym = argv[1]

b.attach_uprobe(name=name, sym=sym, fn_name="trace_start")
b.attach_uretprobe(name=name, sym=sym, fn_name="trace_end")

def print_data(cpu, data, size):
    e = b["output"].event(data)
    print("%-16d %-16d %-4.2f %-16s %-4d %-16d %-16d %-16.6f %-16.6f" % (
        e.clk_delta, e.inst_delta, 1.0* e.inst_delta/e.clk_delta, 
        str(round(e.time_delta * 1e-3, 2)) + ' us', cpu,
        e.chrf_delta, e.chms_delta, 1.0* e.chms_delta/e.chrf_delta,1.0* e.chms_delta/e.clk_delta,))


print("Counters Data")
print("%-16s %-16s %-4s %-16s %-4s %-16s %-16s %-16s %-16s" % (
    'CLOCK', 'INSTRUCTION', 'IPC', 
    'TIME', 'CPU', 
    'CACHE REF', 'CACHE MISS', 'CACHE MISS/all', 'CACHE MISS/sec'))

b["output"].open_perf_buffer(print_data)

PERF_TYPE_HARDWARE = 0
PERF_COUNT_HW_CPU_CYCLES = 0 # not PERF_COUNT_HW_REF_CPU_CYCLES
PERF_COUNT_HW_INSTRUCTIONS = 1
PERF_COUNT_HW_CACHE_REFERENCES = 2
PERF_COUNT_HW_CACHE_MISSES = 3

b["clk"].open_perf_event(PERF_TYPE_HARDWARE, PERF_COUNT_HW_CPU_CYCLES)
b["inst"].open_perf_event(PERF_TYPE_HARDWARE, PERF_COUNT_HW_INSTRUCTIONS)
b["chrf"].open_perf_event(PERF_TYPE_HARDWARE, PERF_COUNT_HW_CACHE_REFERENCES)
b["chms"].open_perf_event(PERF_TYPE_HARDWARE, PERF_COUNT_HW_CACHE_MISSES)

while True:
    try:
        b.perf_buffer_poll()
    except KeyboardInterrupt:
        exit()
