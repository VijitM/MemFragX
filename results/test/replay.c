/* Auto-generated safe replay program */
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <stdint.h>
#include <time.h>

int main() {
    size_t n = 3;
    void **arr = malloc(n * sizeof(void*));
    if (!arr) { perror("malloc"); return 1; }
    size_t i = 0;
    arr[i] = malloc(4194304); if (!arr[i]) { perror("malloc"); return 1; };
    memset(arr[i], 0xAB, 4096);
    i++;
    arr[i] = malloc(2097152); if (!arr[i]) { perror("malloc"); return 1; };
    memset(arr[i], 0xAB, 4096);
    i++;
    arr[i] = malloc(1024); if (!arr[i]) { perror("malloc"); return 1; };
    memset(arr[i], 0xAB, 1024);
    i++;
    printf("[replay] Allocated %zu objects, holding for 3s\n", (size_t)i);
    fflush(stdout);
    struct timespec ts = {8,0}; nanosleep(&ts, NULL);
    for (size_t j=0;j<i;j++) { free(arr[j]); }
    free(arr);
    printf("[replay] Freed and exiting\n"); fflush(stdout);
    return 0;
}
