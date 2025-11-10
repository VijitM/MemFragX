CC = gcc
CFLAGS = -O2 -fPIC -Wall -Wextra
LDFLAGS = -ldl -pthread

all: tracer workload trim_handler

tracer:
	mkdir -p tracer results
	$(CC) $(CFLAGS) -shared tracer/tracer.c -o tracer/libmftrace.so $(LDFLAGS)

workload:
	mkdir -p workload
	$(CC) -O2 workload/workload.c -o workload/workload

trim_handler:
	mkdir -p tools
	$(CC) -O2 -shared -fPIC tools/trim_signal_handler.c -o tools/trim_handler.so

clean:
	rm -f tracer/libmftrace.so workload/workload tools/trim_handler.so
	rm -rf results
	mkdir -p results

.PHONY: all tracer workload trim_handler clean

