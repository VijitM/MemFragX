# ===========================
# MemFragX Project Makefile
# ===========================

CC = gcc
CFLAGS = -O2 -fPIC -Wall -Wextra
LDFLAGS = -ldl -pthread

# Targets
all: tracer workload trim_handler

# ---- Tracer (LD_PRELOAD Library) ----
tracer:
	mkdir -p tracer results
	$(CC) $(CFLAGS) -shared tracer/tracer.c -o tracer/libmftrace.so $(LDFLAGS)

# ---- Workload Generator ----
workload:
	mkdir -p workload
	$(CC) -O2 workload/workload.c -o workload/workload

# ---- Defragmentation Signal Handler ----
trim_handler:
	mkdir -p tools
	$(CC) -O2 -shared -fPIC tools/trim_signal_handler.c -o tools/trim_handler.so

# ---- Clean all build artifacts ----
clean:
	rm -f tracer/libmftrace.so workload/workload tools/trim_handler.so
	rm -rf results
	mkdir -p results

.PHONY: all tracer workload trim_handler clean

