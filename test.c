#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main() {
    printf("[malloc_test] starting allocations...\n");

    void *blocks[5];
    for (int i = 0; i < 5; i++) {
        size_t sz = (i + 1) * 1024 * 1024;
        blocks[i] = malloc(sz);
        if (!blocks[i]) {
            perror("malloc");
            return 1;
        }
        memset(blocks[i], 0xAA, sz);
        printf("[malloc_test] allocated %zu bytes at %p\n", sz, blocks[i]);
        usleep(500000);
    }

    printf("[malloc_test] freeing half of them...\n");
    for (int i = 0; i < 5; i += 2) {
        free(blocks[i]);
        printf("[malloc_test] freed block %d\n", i);
    }

    sleep(2);
    printf("[malloc_test] done.\n");
    return 0;
}

