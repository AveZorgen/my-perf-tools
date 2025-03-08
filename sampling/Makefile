CC = gcc

CFLAGS = -Wall -Wextra -O3

TARGET = sampling
TARGET_G = sampling_g

SRC = sampling.c

BINARY = build

all: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) -o $(TARGET) $(SRC)
	$(CC) $(CFLAGS) -DCALLSTACK -o $(TARGET_G) $(SRC)

	mkdir -p $(BINARY)
	mv $(TARGET) $(BINARY)
	mv $(TARGET_G) $(BINARY)

clean:
	rm -f *.txt *.map -r $(BINARY)

.PHONY: all clean
