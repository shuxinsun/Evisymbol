1. `cpp_demo`:
- Taken from **Retrowrite**. This demo exposes practical usage issues in C++ binaries.
- When the binary is rewritten by Retrowrite and linked with ASan, the - inserted AddressSanitizer instrumentation is able to **successfully detect memory errors**.
(Language: C++; Complier:clang++)

2. `switch_demo`:
- Taken from **Reassessor**. This demo contains a switch construct invoked inside a for loop, which results in the generation of a jump table in the compiled binary.
- It is mainly used to evaluate the handling of **indirect control flow and jump table recovery**.
(Language: C; Complier: clang)
