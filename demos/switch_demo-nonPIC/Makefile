.PHONY: all
all: hello

# This rule tells make how to build hello from hello.cpp
hello: src/hello.c
	clang -o src/hello src/hello.c -save-temps=obj -g
	mkdir -p bin/
	mv src/hello bin/
	mkdir -p asm/
	mv src/*.s asm/

# This rule tells make to delete hello and hello.o
.PHONY: clean
clean:
	# rm src/hello *.bc  *.i  *.o  *.s
	rm -f bin/hello
	rm -f asm/*.s
	rm -f src/*.bc src/*.i src/*.o src/*.s
	rm -f *.bc *.i *.o *.s
