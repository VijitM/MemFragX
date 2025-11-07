/* Auto-generated safe replay program */
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <stdint.h>
#include <time.h>

int main() {
    size_t n = 0;
    void **arr = malloc(n * sizeof(void*));
    if (!arr) { perror("malloc"); return 1; }
    size_t i = 0;
    printf("[replay] Allocated %zu objects, holding for 3s\n", (size_t)i);
    fflush(stdout);
    struct timespec ts = {8,0}; nanosleep(&ts, NULL);
    for (size_t j=0;j<i;j++) { free(arr[j]); }
    free(arr);
    printf("[replay] Freed and exiting\n"); fflush(stdout);
    return 0;
}
