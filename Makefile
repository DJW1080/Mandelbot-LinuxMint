CC = gcc
CFLAGS = -O3 -std=c11 -Wall -Wextra -Werror -fPIC
LIBRARY = build/libmandelbot.so

.PHONY: all test run package
all: $(LIBRARY)

$(LIBRARY): native/mandelbrot.c
	mkdir -p build
	$(CC) $(CFLAGS) -shared $< -o $@ -lm

test: all
	python3 -m unittest discover -s tests -v

run: all
	./bin/mandelbot

package: test
	python3 scripts/build_package.py
