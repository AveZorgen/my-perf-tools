#include <stdio.h>
#include <time.h>
#include <unistd.h>

#define BILLION 1000000000L

#ifdef __cplusplus
extern "C" {
#endif

void __cyg_profile_func_enter(void *this_fn, void *call_site) __attribute__((no_instrument_function));
void __cyg_profile_func_exit(void *this_fn, void *call_site) __attribute__((no_instrument_function));

#ifdef __cplusplus
}
#endif

static FILE *fout;

/*
            max filesize is 1GB
    (in + out) report info is 45 bytes
*/
#define MAX_ENTER ((1 * (1 << 30)) / ((14 + 1) + (14 + 1 + 14 + 1)))
static ssize_t AFTER_MAX_ENTER = 0;

void __cyg_profile_func_enter(void *this_fn, void *) {
    struct timespec time_;
    clock_gettime(CLOCK_MONOTONIC_RAW, &time_);

    static ssize_t ENTERED = 0;
    if (ENTERED < MAX_ENTER) {
        ENTERED++;
        fprintf(fout, "%ld %p\n", BILLION * time_.tv_sec + time_.tv_nsec, this_fn);
    } else {
        AFTER_MAX_ENTER++;
    }
}

void __cyg_profile_func_exit(void *, void *) {
    struct timespec time_;
    clock_gettime(CLOCK_MONOTONIC_RAW, &time_);  // gettimeofday()?

    if (!AFTER_MAX_ENTER) {
        fprintf(fout, "%ld\n", BILLION * time_.tv_sec + time_.tv_nsec);
    } else {
        AFTER_MAX_ENTER--;
    }
}

void __attribute__((constructor)) initLibrary() {
    fout = fopen("out.iprof", "w");
    if (!fout) {
        perror("fopen");
        return;
    }
    char exe_path[4096];  // PATH_MAX
    ssize_t len = readlink("/proc/self/exe", exe_path, sizeof(exe_path) - 1);
    if (len == -1) len = 0;
    exe_path[len] = '\0';

    fputs(exe_path, fout);
    fputs("\nTRACE\n", fout);
}

void __attribute__((destructor)) cleanUpLibrary() {
    fclose(fout);
}

// gcc prof_tracer_simple.c -o prof_tracer_simple.so -shared
// gcc trace_target.c -o trace_target -finstrument-functions -L. -l:./prof_tracer_simple.so
