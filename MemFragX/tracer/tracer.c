#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <dlfcn.h>
#include <pthread.h>
#include <unistd.h>
#include <string.h>
#include <time.h>
#include <sys/syscall.h>

static FILE *log_file = NULL;
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static int initialized = 0;
static int in_hook = 0;

static void* (*real_malloc)(size_t) = NULL;
static void  (*real_free)(void*)   = NULL;
static void* (*real_calloc)(size_t,size_t) = NULL;
static void* (*real_realloc)(void*,size_t) = NULL;

static inline pid_t gettid_wrapper(void) { return (pid_t)syscall(SYS_gettid); }
static inline long long get_time_ns(void) {
    struct timespec ts; clock_gettime(CLOCK_REALTIME, &ts);
    return ((long long)ts.tv_sec * 1000000000LL) + ts.tv_nsec;
}

/* ---- guaranteed early header write ---- */
__attribute__((constructor(101)))   // low priority -> runs first
static void preinit_logger(void) {
    const char *path = getenv("MFTRACE_LOG");
    if (!path) path = "results/mftrace_log.csv";

    FILE *tmp = fopen(path, "w");             // always truncate + new header
    if (tmp) {
        fprintf(tmp, "ts_ns,event,ptr,size,tid\n");
        fflush(tmp);
        fclose(tmp);
        fprintf(stderr, "[mftrace] header written to %s\n", path);
    } else {
        fprintf(stderr, "[mftrace] ERROR: cannot create %s\n", path);
    }
}

/* ---- normal tracer init (opens same file for appending) ---- */
__attribute__((constructor(102)))
static void init_logger(void) {
    if (initialized) return;
    initialized = 1;

    real_malloc = dlsym(RTLD_NEXT, "malloc");
    real_free   = dlsym(RTLD_NEXT, "free");
    real_calloc = dlsym(RTLD_NEXT, "calloc");
    real_realloc= dlsym(RTLD_NEXT, "realloc");

    const char *path = getenv("MFTRACE_LOG");
    if (!path) path = "results/mftrace_log.csv";

    log_file = fopen(path, "a");
    if (!log_file) {
        fprintf(stderr, "[mftrace] ERROR: cannot open %s for append\n", path);
        return;
    }
    setvbuf(log_file, NULL, _IOLBF, 0);
}



// malloc hook
void* malloc(size_t size) {
    if (!real_malloc) real_malloc = dlsym(RTLD_NEXT, "malloc");
    if (in_hook) return real_malloc(size);
    in_hook = 1;

    void *ptr = real_malloc(size);

    if (log_file) {
        pthread_mutex_lock(&lock);
        fprintf(log_file, "%lld,ALLOC,%p,%zu,%d\n",
                get_time_ns(), ptr, size, gettid_wrapper());
        pthread_mutex_unlock(&lock);
    }

    in_hook = 0;
    return ptr;
}

// free hook
void free(void *ptr) {
    if (!real_free) real_free = dlsym(RTLD_NEXT, "free");
    if (in_hook) { real_free(ptr); return; }
    in_hook = 1;

    real_free(ptr);

    if (log_file) {
        pthread_mutex_lock(&lock);
        fprintf(log_file, "%lld,FREE,%p,,%d\n",
                get_time_ns(), ptr, gettid_wrapper());
        pthread_mutex_unlock(&lock);
    }

    in_hook = 0;
}

// calloc hook
void* calloc(size_t nmemb, size_t size) {
    if (!real_calloc) real_calloc = dlsym(RTLD_NEXT, "calloc");
    if (in_hook) return real_calloc(nmemb, size);
    in_hook = 1;

    void *ptr = real_calloc(nmemb, size);

    if (log_file) {
        pthread_mutex_lock(&lock);
        fprintf(log_file, "%lld,CALLOC,%p,%zu,%d\n",
                get_time_ns(), ptr, nmemb * size, gettid_wrapper());
        pthread_mutex_unlock(&lock);
    }

    in_hook = 0;
    return ptr;
}

// realloc hook
void* realloc(void *ptr, size_t size) {
    if (!real_realloc) real_realloc = dlsym(RTLD_NEXT, "realloc");
    if (in_hook) return real_realloc(ptr, size);
    in_hook = 1;

    void *new_ptr = real_realloc(ptr, size);

    if (log_file) {
        pthread_mutex_lock(&lock);
        fprintf(log_file, "%lld,REALLOC,%p,%zu,%d\n",
                get_time_ns(), new_ptr, size, gettid_wrapper());
        pthread_mutex_unlock(&lock);
    }

    in_hook = 0;
    return new_ptr;
}

