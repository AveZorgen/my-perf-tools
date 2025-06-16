CC = gcc
CXX = g++

CFLAGS = -Wall -Wextra -shared -O3

BINARY = build

all: raw agg

install: raw agg
	cp $(BINARY)/* /usr/local/lib
	# sudo ldconfig

raw: tracer_raw.c
	$(CC) $(CFLAGS) -o libtracer_raw.so tracer_raw.c

	mkdir -p $(BINARY)
	mv libtracer_raw.so $(BINARY)

agg: tracer_agg.cpp
	$(CXX) $(CFLAGS) -fPIC -o libtracer_agg.so tracer_agg.cpp

	mkdir -p $(BINARY)
	mv libtracer_agg.so $(BINARY)

clean:
	rm -rf $(BINARY)
