
#include <limits.h>
#include <time.h>
#include <unistd.h>

#include <cstdint>
#include <fstream>
#include <map>
#include <stack>
#include <unordered_map>

#define BILLION 1000000000L

#ifdef __cplusplus
extern "C" {
#endif

void __cyg_profile_func_enter(void *this_fn, void *call_site) __attribute__((no_instrument_function));
void __cyg_profile_func_exit(void *this_fn, void *call_site) __attribute__((no_instrument_function));

#ifdef __cplusplus
}
#endif

struct child_info {
    uint64_t n;
    float self_dur;
};

struct call_info {
    uint64_t n = 0;
    float self_dur = .0f;
    std::unordered_map<void *, child_info> children{};
};

static std::unordered_map<void *, call_info> call_graph_info;

struct call_stack_info {
    void *callee;
    timespec start_time;
    float child_dur;
};

static std::stack<call_stack_info> call_stack;

static void *base_addr = NULL;

void __cyg_profile_func_enter(void *this_fn, void *) {
    struct timespec time_;
    clock_gettime(CLOCK_MONOTONIC_RAW, &time_);

    call_stack.push({this_fn, time_, .0f});

    call_graph_info.emplace(this_fn, call_info());

    if (!base_addr) base_addr = this_fn;  // TODO: think of handling base_addr in another way
}

void __cyg_profile_func_exit(void *, void *) {
    struct timespec time_;
    clock_gettime(CLOCK_MONOTONIC_RAW, &time_);

    const auto top = call_stack.top();
    call_stack.pop();

    const float duration = BILLION * (time_.tv_sec - top.start_time.tv_sec) + time_.tv_nsec - top.start_time.tv_nsec;
    const float self_dur = duration - top.child_dur;

    auto &data = call_graph_info[top.callee];
    data.n++;
    data.self_dur += self_dur;

    if (call_stack.empty()) return;

    auto &parent = call_stack.top();

    parent.child_dur += duration;

    auto &children = call_graph_info[parent.callee].children;
    auto it = children.find(top.callee);
    if (it != children.end()) {
        it->second.n++;
        it->second.self_dur += duration;
    } else {
        children.emplace(top.callee, child_info{1, duration});
    }
}

void __attribute__((destructor)) cleanUpLibrary() {
    std::ofstream out("out.iprof", std::ios::out);

    char exe_path[PATH_MAX];
    ssize_t len = readlink("/proc/self/exe", exe_path, sizeof(exe_path) - 1);
    if (len == -1) len = 0;
    exe_path[len] = '\0';
    out << exe_path;

    out << "\nGRAPH\n"
        << base_addr << "\n";
    for (const auto &entry : call_graph_info) {
        void *caller = entry.first;
        const auto &info = entry.second;
        out << caller << ":" << info.n << " " << info.self_dur << "\n";
        for (const auto &child_entry : info.children) {
            void *callee = child_entry.first;
            const auto &cinfo = child_entry.second;
            out << callee << ":" << cinfo.n << " " << cinfo.self_dur << "|";
        }
        out << std::endl;
    }
    out.close();
}

// g++ prof_tracer_agg.cpp -o prof_tracer_agg.so -shared -fPIC
// gcc trace_target.c -o trace_target -finstrument-functions -L. -l:./prof_tracer_agg.so
