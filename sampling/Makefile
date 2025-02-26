CC = gcc

CFLAGS = -Wall -Wextra -O3

TARGET = sampling

SRC = sampling.c

BINARY = build

all: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) -o $(TARGET) $(SRC)
	mkdir -p $(BINARY)
	mv $(TARGET) $(BINARY)

clean:
	rm -f *.txt *.map -r $(BINARY)

.PHONY: all clean
