CC=clang++
OPT=-O0 -ggdb -Wall -Wpedantic -Wextra -fPIC -fPIE -pie -save-temps=obj

all: simple_inheritance

# This rule tells make how to build demo from simple_inheritance.cpp
simple_inheritance: src/simple_inheritance.cpp
	${CC} ${OPT} src/simple_inheritance.cpp -o src/simple_inheritance
	mkdir -p bin/
	mv src/simple_inheritance bin/
	mkdir -p asm/
	mv src/*.s asm/

# This rule tells make to delete file
.PHONY: clean
clean:
	rm -f bin/simple_inheritance
	rm -f asm/*.s
	rm -f src/*.bc src/*.i src/*.ii src/*.o src/*.s
	rm -f *.bc *.i *.ii *.o *.s
