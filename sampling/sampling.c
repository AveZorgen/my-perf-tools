// Copyright 2025 Kulikov Artem

#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ptrace.h>
#include <sys/time.h>
#include <sys/user.h>
#include <sys/wait.h>
#include <unistd.h>

#define MAX_LINE 3 * 128

#ifdef CALLSTACK
#define MAX_STACK 64
#endif

typedef struct {
    pid_t pid;
    FILE* fout;
} ThreadData;

void* monitor_shared_libraries(void* arg) {
    ThreadData* data = (ThreadData*)arg;
    pid_t pid = data->pid;
    FILE* fout = data->fout;

    char maps_path[32];
    snprintf(maps_path, sizeof(maps_path), "/proc/%d/maps", pid);

    char prev_maps_content[128 * MAX_LINE] = {0};
    char current_maps_content[128 * MAX_LINE] = {0};

    while (1) {
        FILE* maps_file = fopen(maps_path, "r");
        if (!maps_file) {
            perror("fopen");
            break;
        }

        size_t current_size = fread(current_maps_content, 1, sizeof(current_maps_content) - 1, maps_file);
        current_maps_content[current_size] = '\0';
        fclose(maps_file);

        if (strcmp(prev_maps_content, current_maps_content) != 0) {
            fprintf(fout, "%s", current_maps_content);
            strcpy(prev_maps_content, current_maps_content);
        }

        usleep(1000000);  // 1000ms
    }

    return NULL;
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <program-to-trace>\n", argv[0]);
        exit(EXIT_FAILURE);
    }

    pid_t traced_process = fork();
    if (traced_process == 0) {
        char** exec_args = argv + 1;
        execvp(exec_args[0], exec_args);
        perror("execl");
        exit(EXIT_FAILURE);
    } else if (traced_process < 0) {
        perror("fork");
        exit(EXIT_FAILURE);
    }

    FILE* fout = fopen("mpt.txt", "w");
    if (!fout) {
        perror("fopen");
        exit(EXIT_FAILURE);
    }

    FILE* fmap = fopen("mpt.map", "w");
    if (!fmap) {
        perror("fopen");
        fclose(fout);
        exit(EXIT_FAILURE);
    }

    ThreadData thread_data = {traced_process, fmap};
    pthread_t monitor_thread;

    if (pthread_create(&monitor_thread, NULL, monitor_shared_libraries, &thread_data) != 0) {
        perror("pthread_create");
        fclose(fmap);
        fclose(fout);
        exit(EXIT_FAILURE);
    }

    ptrace(PTRACE_SEIZE, traced_process, NULL, NULL);
    while (1) {
        ptrace(PTRACE_INTERRUPT, traced_process, NULL, NULL);
        int status;
        wait(&status);
        if (WIFEXITED(status) || WIFSIGNALED(status)) {
            break;
        }

        struct user_regs_struct regs;
        ptrace(PTRACE_GETREGS, traced_process, NULL, &regs);

        long long ip = regs.rip;

#ifdef CALLSTACK
        long long bp = regs.rbp;
        long ret = ptrace(PTRACE_PEEKDATA, traced_process, bp + sizeof(long), NULL);

        static long stack[MAX_STACK];
        int cur_depth = 0;
        while (cur_depth < MAX_STACK && bp != -1 && ret != -1) {
            stack[cur_depth++] = ret;

            bp = ptrace(PTRACE_PEEKDATA, traced_process, bp, NULL);
            ret = ptrace(PTRACE_PEEKDATA, traced_process, bp + sizeof(long), NULL);
        }

        ptrace(PTRACE_CONT, traced_process, NULL, NULL);

        fprintf(fout, "0x%llx", ip);
        for (int i = 0; i < cur_depth; i++) {
            fprintf(fout, " 0x%lx", stack[i]);
        }
        fprintf(fout, "\n");
#else
        ptrace(PTRACE_CONT, traced_process, NULL, NULL);

        fprintf(fout, "0x%llx\n", ip);
#endif

        usleep(1000);  // 1ms
    }

    pthread_cancel(monitor_thread);
    pthread_join(monitor_thread, NULL);

    fclose(fmap);
    fclose(fout);
    return 0;
}
