#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <errno.h>
#include <malloc.h>

// Enhanced workload generator with deterministic disk-heavy mode and a hook point for malloc_trim.
// Usage:
//   ./workload <pattern> <ops> <max_size> [disk] [trim-at-step]
// pattern: uniform | burst | pareto
// ops: number of operations
// max_size: max allocation size in bytes
// disk: optional "disk" to perform file-backed mmap reads
// trim-at-step: optional integer; if provided, calls malloc_trim(0) after that many ops

static unsigned long xor_shift() {
    static unsigned long x = 88172645463325252ULL;
    x ^= x << 13;
    x ^= x >> 7;
    x ^= x << 17;
    return x;
}

int main(int argc, char **argv) {
    if (argc < 4) {
        fprintf(stderr, "usage: %s <pattern> <ops> <max_size> [disk] [trim-at-step]\n", argv[0]);
        return 1;
    }
    const char *pattern = argv[1];
    long ops = atol(argv[2]);
    long max_size = atol(argv[3]);
    int do_disk = (argc >= 5 && strcmp(argv[4], "disk") == 0);
    long trim_at = (argc >= 6) ? atol(argv[5]) : -1;

    void **slots = calloc(200000, sizeof(void*));
    int nslots = 200000;
    if (!slots) { perror("calloc"); return 1; }

    // Prepare a temp file for mmap reads when disk mode is enabled
    int tmpfd = -1;
    size_t tmp_size = 64 * 1024 * 1024; // 64MB
    if (do_disk) {
        char tmpname[] = "/tmp/memfragx_tmpXXXXXX";
        tmpfd = mkstemp(tmpname);
        if (tmpfd < 0) { perror("mkstemp"); return 1; }
        unlink(tmpname); // file removed but fd stays valid
        // ensure the file is tmp_size with write
        if (ftruncate(tmpfd, tmp_size) != 0) { perror("ftruncate"); return 1; }
        // write a page at start and end to ensure pages exist
        void *map = mmap(NULL, 4096, PROT_READ|PROT_WRITE, MAP_SHARED, tmpfd, 0);
        if (map != MAP_FAILED) {
            memset(map, 0xAA, 4096);
            munmap(map, 4096);
        }
    }

    for (long i = 0; i < ops; ++i) {
        int idx = xor_shift() % nslots;
        if (slots[idx]) {
            free(slots[idx]);
            slots[idx] = NULL;
        }
        size_t size = 0;
        if (strcmp(pattern, "uniform") == 0) {
            size = 1 + (xor_shift() % max_size);
        } else if (strcmp(pattern, "burst") == 0) {
            if ((xor_shift() % 100) < 10) size = 1 + (xor_shift() % max_size);
            else size = 1 + (xor_shift() % (max_size/10 + 1));
        } else if (strcmp(pattern, "pareto") == 0) {
            int r = xor_shift() % 1000;
            if (r < 5) size = 1 + (xor_shift() % max_size);
            else size = 1 + (xor_shift() % (max_size/20 + 1));
        } else {
            size = 1 + (xor_shift() % max_size);
        }
        slots[idx] = malloc(size);
        if (!slots[idx]) { perror("malloc"); return 1; }

        // Disk activity: mmap and touch a chunk every 500 ops
        if (do_disk && (i % 500) == 0) {
            size_t offset = (xor_shift() % (tmp_size - 4096));
            void *m = mmap(NULL, 4096, PROT_READ, MAP_SHARED, tmpfd, offset);
            if (m != MAP_FAILED) {
                volatile char c = ((char*)m)[0];
                (void)c;
                munmap(m, 4096);
            }
        }

        // optional trim point for Approach A demo
        if (trim_at > 0 && i == trim_at) {
            malloc_trim(0); // return top-of-heap to OS
        }

        if ((i % 10000) == 0) usleep(1000);
    }

    for (int i=0;i<nslots;i++) if (slots[i]) free(slots[i]);
    free(slots);
    if (tmpfd >= 0) close(tmpfd);
    return 0;
}
