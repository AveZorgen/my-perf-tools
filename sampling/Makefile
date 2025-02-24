CC = gcc

CFLAGS = -Wall -O3 -g

TARGET = sampling

SRC = sampling.c

all: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) -o $(TARGET) $(SRC)

clean:
	rm -f *.txt *.map $(TARGET)

.PHONY: all clean
