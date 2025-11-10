#define _GNU_SOURCE
#include <signal.h>
#include <stdio.h>
#include <malloc.h>
#include <unistd.h>

static void handle_trim(int signum) {
    (void)signum;
    malloc_trim(0);
    fprintf(stderr, "malloc_trim(0) invoked via signal\n");
}

__attribute__((constructor)) static void install() {
    struct sigaction sa;
    sa.sa_handler = handle_trim;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = SA_RESTART;
    sigaction(SIGUSR1, &sa, NULL);
}
