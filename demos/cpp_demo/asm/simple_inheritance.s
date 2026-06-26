	.text
	.file	"simple_inheritance.cpp"
	.globl	main                    # -- Begin function main
	.p2align	4, 0x90
	.type	main,@function
main:                                   # @main
.Lfunc_begin0:
	.file	1 "src" "simple_inheritance.cpp"
	.loc	1 11 0                  # src/simple_inheritance.cpp:11:0
	.cfi_startproc
# %bb.0:
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset %rbp, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register %rbp
	subq	$48, %rsp
	movl	$0, -4(%rbp)
	movl	%edi, -8(%rbp)
	movq	%rsi, -16(%rbp)
.Ltmp0:
	.loc	1 14 12 prologue_end    # src/simple_inheritance.cpp:14:12
	cmpl	$0, -8(%rbp)
.Ltmp1:
	.loc	1 14 7 is_stmt 0        # src/simple_inheritance.cpp:14:7
	jne	.LBB0_2
# %bb.1:
	.loc	1 0 7                   # src/simple_inheritance.cpp:0:7
	movl	$8, %eax
	movl	%eax, %edi
.Ltmp2:
	.loc	1 15 13 is_stmt 1       # src/simple_inheritance.cpp:15:13
	callq	_Znwm@PLT
	xorl	%esi, %esi
	movl	$8, %ecx
	movl	%ecx, %edx
	.loc	1 15 17 is_stmt 0       # src/simple_inheritance.cpp:15:17
	movq	%rax, %rdi
	movq	%rax, -32(%rbp)         # 8-byte Spill
	callq	memset@PLT
	movq	-32(%rbp), %rdi         # 8-byte Reload
	callq	_ZN5ShapeC2Ev
	.loc	1 15 11                 # src/simple_inheritance.cpp:15:11
	movq	-32(%rbp), %rax         # 8-byte Reload
	movq	%rax, -24(%rbp)
	.loc	1 16 3 is_stmt 1        # src/simple_inheritance.cpp:16:3
	jmp	.LBB0_3
.Ltmp3:
.LBB0_2:
	.loc	1 0 3 is_stmt 0         # src/simple_inheritance.cpp:0:3
	movl	$8, %eax
	movl	%eax, %edi
.Ltmp4:
	.loc	1 17 13 is_stmt 1       # src/simple_inheritance.cpp:17:13
	callq	_Znwm@PLT
	xorl	%esi, %esi
	movl	$8, %ecx
	movl	%ecx, %edx
	.loc	1 17 17 is_stmt 0       # src/simple_inheritance.cpp:17:17
	movq	%rax, %rdi
	movq	%rax, -40(%rbp)         # 8-byte Spill
	callq	memset@PLT
	movq	-40(%rbp), %rdi         # 8-byte Reload
	callq	_ZN9RectangleC2Ev
	.loc	1 17 13                 # src/simple_inheritance.cpp:17:13
	movq	-40(%rbp), %rax         # 8-byte Reload
	.loc	1 17 11                 # src/simple_inheritance.cpp:17:11
	movq	%rax, -24(%rbp)
.Ltmp5:
.LBB0_3:
	.loc	1 20 3 is_stmt 1        # src/simple_inheritance.cpp:20:3
	movq	-24(%rbp), %rax
	.loc	1 20 10 is_stmt 0       # src/simple_inheritance.cpp:20:10
	movq	(%rax), %rcx
	movq	%rax, %rdi
	callq	*(%rcx)
	.loc	1 21 10 is_stmt 1       # src/simple_inheritance.cpp:21:10
	movq	-24(%rbp), %rax
	.loc	1 21 3 is_stmt 0        # src/simple_inheritance.cpp:21:3
	cmpq	$0, %rax
	movq	%rax, -48(%rbp)         # 8-byte Spill
	je	.LBB0_5
# %bb.4:
	movq	-48(%rbp), %rax         # 8-byte Reload
	movq	%rax, %rdi
	callq	_ZdlPv@PLT
.LBB0_5:
	.loc	1 22 1 is_stmt 1        # src/simple_inheritance.cpp:22:1
	movl	-4(%rbp), %eax
	addq	$48, %rsp
	popq	%rbp
	retq
.Ltmp6:
.Lfunc_end0:
	.size	main, .Lfunc_end0-main
	.cfi_endproc
                                        # -- End function
	.section	.text._ZN5ShapeC2Ev,"axG",@progbits,_ZN5ShapeC2Ev,comdat
	.weak	_ZN5ShapeC2Ev           # -- Begin function _ZN5ShapeC2Ev
	.p2align	4, 0x90
	.type	_ZN5ShapeC2Ev,@function
_ZN5ShapeC2Ev:                          # @_ZN5ShapeC2Ev
.Lfunc_begin1:
	.loc	1 1 0                   # src/simple_inheritance.cpp:1:0
	.cfi_startproc
# %bb.0:
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset %rbp, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register %rbp
	leaq	_ZTV5Shape(%rip), %rax
	addq	$16, %rax
	movq	%rdi, -8(%rbp)
	movq	-8(%rbp), %rdi
.Ltmp7:
	.loc	1 1 7 prologue_end      # src/simple_inheritance.cpp:1:7
	movq	%rax, (%rdi)
	popq	%rbp
	retq
.Ltmp8:
.Lfunc_end1:
	.size	_ZN5ShapeC2Ev, .Lfunc_end1-_ZN5ShapeC2Ev
	.cfi_endproc
                                        # -- End function
	.section	.text._ZN9RectangleC2Ev,"axG",@progbits,_ZN9RectangleC2Ev,comdat
	.weak	_ZN9RectangleC2Ev       # -- Begin function _ZN9RectangleC2Ev
	.p2align	4, 0x90
	.type	_ZN9RectangleC2Ev,@function
_ZN9RectangleC2Ev:                      # @_ZN9RectangleC2Ev
.Lfunc_begin2:
	.loc	1 6 0                   # src/simple_inheritance.cpp:6:0
	.cfi_startproc
# %bb.0:
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset %rbp, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register %rbp
	subq	$16, %rsp
	movq	%rdi, -8(%rbp)
	movq	-8(%rbp), %rdi
.Ltmp9:
	.loc	1 6 7 prologue_end      # src/simple_inheritance.cpp:6:7
	movq	%rdi, %rax
	movq	%rdi, -16(%rbp)         # 8-byte Spill
	movq	%rax, %rdi
	callq	_ZN5ShapeC2Ev
	leaq	_ZTV9Rectangle(%rip), %rax
	addq	$16, %rax
	movq	-16(%rbp), %rdi         # 8-byte Reload
	movq	%rax, (%rdi)
	addq	$16, %rsp
	popq	%rbp
	retq
.Ltmp10:
.Lfunc_end2:
	.size	_ZN9RectangleC2Ev, .Lfunc_end2-_ZN9RectangleC2Ev
	.cfi_endproc
                                        # -- End function
	.section	.text._ZN5Shape4drawEv,"axG",@progbits,_ZN5Shape4drawEv,comdat
	.weak	_ZN5Shape4drawEv        # -- Begin function _ZN5Shape4drawEv
	.p2align	4, 0x90
	.type	_ZN5Shape4drawEv,@function
_ZN5Shape4drawEv:                       # @_ZN5Shape4drawEv
.Lfunc_begin3:
	.loc	1 3 0                   # src/simple_inheritance.cpp:3:0
	.cfi_startproc
# %bb.0:
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset %rbp, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register %rbp
	movq	%rdi, -8(%rbp)
.Ltmp11:
	.loc	1 3 24 prologue_end     # src/simple_inheritance.cpp:3:24
	popq	%rbp
	retq
.Ltmp12:
.Lfunc_end3:
	.size	_ZN5Shape4drawEv, .Lfunc_end3-_ZN5Shape4drawEv
	.cfi_endproc
                                        # -- End function
	.section	.text._ZN9Rectangle4drawEv,"axG",@progbits,_ZN9Rectangle4drawEv,comdat
	.weak	_ZN9Rectangle4drawEv    # -- Begin function _ZN9Rectangle4drawEv
	.p2align	4, 0x90
	.type	_ZN9Rectangle4drawEv,@function
_ZN9Rectangle4drawEv:                   # @_ZN9Rectangle4drawEv
.Lfunc_begin4:
	.loc	1 8 0                   # src/simple_inheritance.cpp:8:0
	.cfi_startproc
# %bb.0:
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset %rbp, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register %rbp
	movq	%rdi, -8(%rbp)
.Ltmp13:
	.loc	1 8 24 prologue_end     # src/simple_inheritance.cpp:8:24
	popq	%rbp
	retq
.Ltmp14:
.Lfunc_end4:
	.size	_ZN9Rectangle4drawEv, .Lfunc_end4-_ZN9Rectangle4drawEv
	.cfi_endproc
                                        # -- End function
	.type	_ZTV5Shape,@object      # @_ZTV5Shape
	.section	.data.rel.ro._ZTV5Shape,"aGw",@progbits,_ZTV5Shape,comdat
	.weak	_ZTV5Shape
	.p2align	3
_ZTV5Shape:
	.quad	0
	.quad	_ZTI5Shape
	.quad	_ZN5Shape4drawEv
	.size	_ZTV5Shape, 24

	.type	_ZTS5Shape,@object      # @_ZTS5Shape
	.section	.rodata._ZTS5Shape,"aG",@progbits,_ZTS5Shape,comdat
	.weak	_ZTS5Shape
_ZTS5Shape:
	.asciz	"5Shape"
	.size	_ZTS5Shape, 7

	.type	_ZTI5Shape,@object      # @_ZTI5Shape
	.section	.data.rel.ro._ZTI5Shape,"aGw",@progbits,_ZTI5Shape,comdat
	.weak	_ZTI5Shape
	.p2align	3
_ZTI5Shape:
	.quad	_ZTVN10__cxxabiv117__class_type_infoE+16
	.quad	_ZTS5Shape
	.size	_ZTI5Shape, 16

	.type	_ZTV9Rectangle,@object  # @_ZTV9Rectangle
	.section	.data.rel.ro._ZTV9Rectangle,"aGw",@progbits,_ZTV9Rectangle,comdat
	.weak	_ZTV9Rectangle
	.p2align	3
_ZTV9Rectangle:
	.quad	0
	.quad	_ZTI9Rectangle
	.quad	_ZN9Rectangle4drawEv
	.size	_ZTV9Rectangle, 24

	.type	_ZTS9Rectangle,@object  # @_ZTS9Rectangle
	.section	.rodata._ZTS9Rectangle,"aG",@progbits,_ZTS9Rectangle,comdat
	.weak	_ZTS9Rectangle
_ZTS9Rectangle:
	.asciz	"9Rectangle"
	.size	_ZTS9Rectangle, 11

	.type	_ZTI9Rectangle,@object  # @_ZTI9Rectangle
	.section	.data.rel.ro._ZTI9Rectangle,"aGw",@progbits,_ZTI9Rectangle,comdat
	.weak	_ZTI9Rectangle
	.p2align	4
_ZTI9Rectangle:
	.quad	_ZTVN10__cxxabiv120__si_class_type_infoE+16
	.quad	_ZTS9Rectangle
	.quad	_ZTI5Shape
	.size	_ZTI9Rectangle, 24

	.file	2 "<stdin>"
	.section	.debug_str,"MS",@progbits,1
.Linfo_string0:
	.asciz	"clang version 6.0.0-1ubuntu2 (tags/RELEASE_600/final)" # string offset=0
.Linfo_string1:
	.asciz	"src/simple_inheritance.cpp" # string offset=54
.Linfo_string2:
	.asciz	"/home/ssx/Desktop/myProject/demos/cpp_demo" # string offset=81
.Linfo_string3:
	.asciz	"_vptr$Shape"           # string offset=124
.Linfo_string4:
	.asciz	"int"                   # string offset=136
.Linfo_string5:
	.asciz	"__vtbl_ptr_type"       # string offset=140
.Linfo_string6:
	.asciz	"_ZN5Shape4drawEv"      # string offset=156
.Linfo_string7:
	.asciz	"draw"                  # string offset=173
.Linfo_string8:
	.asciz	"Shape"                 # string offset=178
.Linfo_string9:
	.asciz	"_ZN9Rectangle4drawEv"  # string offset=184
.Linfo_string10:
	.asciz	"Rectangle"             # string offset=205
.Linfo_string11:
	.asciz	"main"                  # string offset=215
.Linfo_string12:
	.asciz	"_ZN5ShapeC2Ev"         # string offset=220
.Linfo_string13:
	.asciz	"_ZN9RectangleC2Ev"     # string offset=234
.Linfo_string14:
	.asciz	"argc"                  # string offset=252
.Linfo_string15:
	.asciz	"argv"                  # string offset=257
.Linfo_string16:
	.asciz	"char"                  # string offset=262
.Linfo_string17:
	.asciz	"shape"                 # string offset=267
.Linfo_string18:
	.asciz	"this"                  # string offset=273
	.section	.debug_abbrev,"",@progbits
	.byte	1                       # Abbreviation Code
	.byte	17                      # DW_TAG_compile_unit
	.byte	1                       # DW_CHILDREN_yes
	.byte	37                      # DW_AT_producer
	.byte	14                      # DW_FORM_strp
	.byte	19                      # DW_AT_language
	.byte	5                       # DW_FORM_data2
	.byte	3                       # DW_AT_name
	.byte	14                      # DW_FORM_strp
	.byte	16                      # DW_AT_stmt_list
	.byte	23                      # DW_FORM_sec_offset
	.byte	27                      # DW_AT_comp_dir
	.byte	14                      # DW_FORM_strp
	.ascii	"\264B"                 # DW_AT_GNU_pubnames
	.byte	25                      # DW_FORM_flag_present
	.byte	17                      # DW_AT_low_pc
	.byte	1                       # DW_FORM_addr
	.byte	85                      # DW_AT_ranges
	.byte	23                      # DW_FORM_sec_offset
	.byte	0                       # EOM(1)
	.byte	0                       # EOM(2)
	.byte	2                       # Abbreviation Code
	.byte	46                      # DW_TAG_subprogram
	.byte	1                       # DW_CHILDREN_yes
	.byte	17                      # DW_AT_low_pc
	.byte	1                       # DW_FORM_addr
	.byte	18                      # DW_AT_high_pc
	.byte	6                       # DW_FORM_data4
	.byte	64                      # DW_AT_frame_base
	.byte	24                      # DW_FORM_exprloc
	.byte	3                       # DW_AT_name
	.byte	14                      # DW_FORM_strp
	.byte	58                      # DW_AT_decl_file
	.byte	11                      # DW_FORM_data1
	.byte	59                      # DW_AT_decl_line
	.byte	11                      # DW_FORM_data1
	.byte	73                      # DW_AT_type
	.byte	19                      # DW_FORM_ref4
	.byte	63                      # DW_AT_external
	.byte	25                      # DW_FORM_flag_present
	.byte	0                       # EOM(1)
	.byte	0                       # EOM(2)
	.byte	3                       # Abbreviation Code
	.byte	5                       # DW_TAG_formal_parameter
	.byte	0                       # DW_CHILDREN_no
	.byte	2                       # DW_AT_location
	.byte	24                      # DW_FORM_exprloc
	.byte	3                       # DW_AT_name
	.byte	14                      # DW_FORM_strp
	.byte	58                      # DW_AT_decl_file
	.byte	11                      # DW_FORM_data1
	.byte	59                      # DW_AT_decl_line
	.byte	11                      # DW_FORM_data1
	.byte	73                      # DW_AT_type
	.byte	19                      # DW_FORM_ref4
	.byte	0                       # EOM(1)
	.byte	0                       # EOM(2)
	.byte	4                       # Abbreviation Code
	.byte	52                      # DW_TAG_variable
	.byte	0                       # DW_CHILDREN_no
	.byte	2                       # DW_AT_location
	.byte	24                      # DW_FORM_exprloc
	.byte	3                       # DW_AT_name
	.byte	14                      # DW_FORM_strp
	.byte	58                      # DW_AT_decl_file
	.byte	11                      # DW_FORM_data1
	.byte	59                      # DW_AT_decl_line
	.byte	11                      # DW_FORM_data1
	.byte	73                      # DW_AT_type
	.byte	19                      # DW_FORM_ref4
	.byte	0                       # EOM(1)
	.byte	0                       # EOM(2)
	.byte	5                       # Abbreviation Code
	.byte	2                       # DW_TAG_class_type
	.byte	1                       # DW_CHILDREN_yes
	.byte	29                      # DW_AT_containing_type
	.byte	19                      # DW_FORM_ref4
	.byte	3                       # DW_AT_name
	.byte	14                      # DW_FORM_strp
	.byte	11                      # DW_AT_byte_size
	.byte	11                      # DW_FORM_data1
	.byte	58                      # DW_AT_decl_file
	.byte	11                      # DW_FORM_data1
	.byte	59                      # DW_AT_decl_line
	.byte	11                      # DW_FORM_data1
	.byte	0                       # EOM(1)
	.byte	0                       # EOM(2)
	.byte	6                       # Abbreviation Code
	.byte	13                      # DW_TAG_member
	.byte	0                       # DW_CHILDREN_no
	.byte	3                       # DW_AT_name
	.byte	14                      # DW_FORM_strp
	.byte	73                      # DW_AT_type
	.byte	19                      # DW_FORM_ref4
	.byte	56                      # DW_AT_data_member_location
	.byte	11                      # DW_FORM_data1
	.byte	52                      # DW_AT_artificial
	.byte	25                      # DW_FORM_flag_present
	.byte	0                       # EOM(1)
	.byte	0                       # EOM(2)
	.byte	7                       # Abbreviation Code
	.byte	46                      # DW_TAG_subprogram
	.byte	1                       # DW_CHILDREN_yes
	.byte	110                     # DW_AT_linkage_name
	.byte	14                      # DW_FORM_strp
	.byte	3                       # DW_AT_name
	.byte	14                      # DW_FORM_strp
	.byte	58                      # DW_AT_decl_file
	.byte	11                      # DW_FORM_data1
	.byte	59                      # DW_AT_decl_line
	.byte	11                      # DW_FORM_data1
	.byte	76                      # DW_AT_virtuality
	.byte	11                      # DW_FORM_data1
	.byte	77                      # DW_AT_vtable_elem_location
	.byte	24                      # DW_FORM_exprloc
	.byte	60                      # DW_AT_declaration
	.byte	25                      # DW_FORM_flag_present
	.byte	63                      # DW_AT_external
	.byte	25                      # DW_FORM_flag_present
	.byte	50                      # DW_AT_accessibility
	.byte	11                      # DW_FORM_data1
	.byte	29                      # DW_AT_containing_type
	.byte	19                      # DW_FORM_ref4
	.byte	0                       # EOM(1)
	.byte	0                       # EOM(2)
	.byte	8                       # Abbreviation Code
	.byte	5                       # DW_TAG_formal_parameter
	.byte	0                       # DW_CHILDREN_no
	.byte	73                      # DW_AT_type
	.byte	19                      # DW_FORM_ref4
	.byte	52                      # DW_AT_artificial
	.byte	25                      # DW_FORM_flag_present
	.byte	0                       # EOM(1)
	.byte	0                       # EOM(2)
	.byte	9                       # Abbreviation Code
	.byte	46                      # DW_TAG_subprogram
	.byte	1                       # DW_CHILDREN_yes
	.byte	3                       # DW_AT_name
	.byte	14                      # DW_FORM_strp
	.byte	60                      # DW_AT_declaration
	.byte	25                      # DW_FORM_flag_present
	.byte	52                      # DW_AT_artificial
	.byte	25                      # DW_FORM_flag_present
	.byte	63                      # DW_AT_external
	.byte	25                      # DW_FORM_flag_present
	.byte	50                      # DW_AT_accessibility
	.byte	11                      # DW_FORM_data1
	.byte	0                       # EOM(1)
	.byte	0                       # EOM(2)
	.byte	10                      # Abbreviation Code
	.byte	15                      # DW_TAG_pointer_type
	.byte	0                       # DW_CHILDREN_no
	.byte	73                      # DW_AT_type
	.byte	19                      # DW_FORM_ref4
	.byte	0                       # EOM(1)
	.byte	0                       # EOM(2)
	.byte	11                      # Abbreviation Code
	.byte	15                      # DW_TAG_pointer_type
	.byte	0                       # DW_CHILDREN_no
	.byte	73                      # DW_AT_type
	.byte	19                      # DW_FORM_ref4
	.byte	3                       # DW_AT_name
	.byte	14                      # DW_FORM_strp
	.byte	0                       # EOM(1)
	.byte	0                       # EOM(2)
	.byte	12                      # Abbreviation Code
	.byte	21                      # DW_TAG_subroutine_type
	.byte	0                       # DW_CHILDREN_no
	.byte	73                      # DW_AT_type
	.byte	19                      # DW_FORM_ref4
	.byte	0                       # EOM(1)
	.byte	0                       # EOM(2)
	.byte	13                      # Abbreviation Code
	.byte	36                      # DW_TAG_base_type
	.byte	0                       # DW_CHILDREN_no
	.byte	3                       # DW_AT_name
	.byte	14                      # DW_FORM_strp
	.byte	62                      # DW_AT_encoding
	.byte	11                      # DW_FORM_data1
	.byte	11                      # DW_AT_byte_size
	.byte	11                      # DW_FORM_data1
	.byte	0                       # EOM(1)
	.byte	0                       # EOM(2)
	.byte	14                      # Abbreviation Code
	.byte	46                      # DW_TAG_subprogram
	.byte	1                       # DW_CHILDREN_yes
	.byte	17                      # DW_AT_low_pc
	.byte	1                       # DW_FORM_addr
	.byte	18                      # DW_AT_high_pc
	.byte	6                       # DW_FORM_data4
	.byte	64                      # DW_AT_frame_base
	.byte	24                      # DW_FORM_exprloc
	.byte	100                     # DW_AT_object_pointer
	.byte	19                      # DW_FORM_ref4
	.byte	58                      # DW_AT_decl_file
	.byte	11                      # DW_FORM_data1
	.byte	59                      # DW_AT_decl_line
	.byte	11                      # DW_FORM_data1
	.byte	110                     # DW_AT_linkage_name
	.byte	14                      # DW_FORM_strp
	.byte	71                      # DW_AT_specification
	.byte	19                      # DW_FORM_ref4
	.byte	0                       # EOM(1)
	.byte	0                       # EOM(2)
	.byte	15                      # Abbreviation Code
	.byte	5                       # DW_TAG_formal_parameter
	.byte	0                       # DW_CHILDREN_no
	.byte	2                       # DW_AT_location
	.byte	24                      # DW_FORM_exprloc
	.byte	3                       # DW_AT_name
	.byte	14                      # DW_FORM_strp
	.byte	73                      # DW_AT_type
	.byte	19                      # DW_FORM_ref4
	.byte	52                      # DW_AT_artificial
	.byte	25                      # DW_FORM_flag_present
	.byte	0                       # EOM(1)
	.byte	0                       # EOM(2)
	.byte	16                      # Abbreviation Code
	.byte	28                      # DW_TAG_inheritance
	.byte	0                       # DW_CHILDREN_no
	.byte	73                      # DW_AT_type
	.byte	19                      # DW_FORM_ref4
	.byte	56                      # DW_AT_data_member_location
	.byte	11                      # DW_FORM_data1
	.byte	50                      # DW_AT_accessibility
	.byte	11                      # DW_FORM_data1
	.byte	0                       # EOM(1)
	.byte	0                       # EOM(2)
	.byte	17                      # Abbreviation Code
	.byte	46                      # DW_TAG_subprogram
	.byte	1                       # DW_CHILDREN_yes
	.byte	17                      # DW_AT_low_pc
	.byte	1                       # DW_FORM_addr
	.byte	18                      # DW_AT_high_pc
	.byte	6                       # DW_FORM_data4
	.byte	64                      # DW_AT_frame_base
	.byte	24                      # DW_FORM_exprloc
	.byte	100                     # DW_AT_object_pointer
	.byte	19                      # DW_FORM_ref4
	.byte	71                      # DW_AT_specification
	.byte	19                      # DW_FORM_ref4
	.byte	0                       # EOM(1)
	.byte	0                       # EOM(2)
	.byte	0                       # EOM(3)
	.section	.debug_info,"",@progbits
.Lcu_begin0:
	.long	445                     # Length of Unit
	.short	4                       # DWARF version number
	.long	.debug_abbrev           # Offset Into Abbrev. Section
	.byte	8                       # Address Size (in bytes)
	.byte	1                       # Abbrev [1] 0xb:0x1b6 DW_TAG_compile_unit
	.long	.Linfo_string0          # DW_AT_producer
	.short	4                       # DW_AT_language
	.long	.Linfo_string1          # DW_AT_name
	.long	.Lline_table_start0     # DW_AT_stmt_list
	.long	.Linfo_string2          # DW_AT_comp_dir
                                        # DW_AT_GNU_pubnames
	.quad	0                       # DW_AT_low_pc
	.long	.Ldebug_ranges0         # DW_AT_ranges
	.byte	2                       # Abbrev [2] 0x2a:0x44 DW_TAG_subprogram
	.quad	.Lfunc_begin0           # DW_AT_low_pc
	.long	.Lfunc_end0-.Lfunc_begin0 # DW_AT_high_pc
	.byte	1                       # DW_AT_frame_base
	.byte	86
	.long	.Linfo_string11         # DW_AT_name
	.byte	1                       # DW_AT_decl_file
	.byte	11                      # DW_AT_decl_line
	.long	190                     # DW_AT_type
                                        # DW_AT_external
	.byte	3                       # Abbrev [3] 0x43:0xe DW_TAG_formal_parameter
	.byte	2                       # DW_AT_location
	.byte	145
	.byte	120
	.long	.Linfo_string14         # DW_AT_name
	.byte	1                       # DW_AT_decl_file
	.byte	11                      # DW_AT_decl_line
	.long	190                     # DW_AT_type
	.byte	3                       # Abbrev [3] 0x51:0xe DW_TAG_formal_parameter
	.byte	2                       # DW_AT_location
	.byte	145
	.byte	112
	.long	.Linfo_string15         # DW_AT_name
	.byte	1                       # DW_AT_decl_file
	.byte	11                      # DW_AT_decl_line
	.long	421                     # DW_AT_type
	.byte	4                       # Abbrev [4] 0x5f:0xe DW_TAG_variable
	.byte	2                       # DW_AT_location
	.byte	145
	.byte	104
	.long	.Linfo_string17         # DW_AT_name
	.byte	1                       # DW_AT_decl_file
	.byte	12                      # DW_AT_decl_line
	.long	438                     # DW_AT_type
	.byte	0                       # End Of Children Mark
	.byte	5                       # Abbrev [5] 0x6e:0x3d DW_TAG_class_type
	.long	110                     # DW_AT_containing_type
	.long	.Linfo_string8          # DW_AT_name
	.byte	8                       # DW_AT_byte_size
	.byte	1                       # DW_AT_decl_file
	.byte	1                       # DW_AT_decl_line
	.byte	6                       # Abbrev [6] 0x7a:0xa DW_TAG_member
	.long	.Linfo_string3          # DW_AT_name
	.long	171                     # DW_AT_type
	.byte	0                       # DW_AT_data_member_location
                                        # DW_AT_artificial
	.byte	7                       # Abbrev [7] 0x84:0x1a DW_TAG_subprogram
	.long	.Linfo_string6          # DW_AT_linkage_name
	.long	.Linfo_string7          # DW_AT_name
	.byte	1                       # DW_AT_decl_file
	.byte	3                       # DW_AT_decl_line
	.byte	1                       # DW_AT_virtuality
	.byte	2                       # DW_AT_vtable_elem_location
	.byte	16
	.byte	0
                                        # DW_AT_declaration
                                        # DW_AT_external
	.byte	1                       # DW_AT_accessibility
                                        # DW_ACCESS_public
	.long	110                     # DW_AT_containing_type
	.byte	8                       # Abbrev [8] 0x98:0x5 DW_TAG_formal_parameter
	.long	197                     # DW_AT_type
                                        # DW_AT_artificial
	.byte	0                       # End Of Children Mark
	.byte	9                       # Abbrev [9] 0x9e:0xc DW_TAG_subprogram
	.long	.Linfo_string8          # DW_AT_name
                                        # DW_AT_declaration
                                        # DW_AT_artificial
                                        # DW_AT_external
	.byte	1                       # DW_AT_accessibility
                                        # DW_ACCESS_public
	.byte	8                       # Abbrev [8] 0xa4:0x5 DW_TAG_formal_parameter
	.long	197                     # DW_AT_type
                                        # DW_AT_artificial
	.byte	0                       # End Of Children Mark
	.byte	0                       # End Of Children Mark
	.byte	10                      # Abbrev [10] 0xab:0x5 DW_TAG_pointer_type
	.long	176                     # DW_AT_type
	.byte	11                      # Abbrev [11] 0xb0:0x9 DW_TAG_pointer_type
	.long	185                     # DW_AT_type
	.long	.Linfo_string5          # DW_AT_name
	.byte	12                      # Abbrev [12] 0xb9:0x5 DW_TAG_subroutine_type
	.long	190                     # DW_AT_type
	.byte	13                      # Abbrev [13] 0xbe:0x7 DW_TAG_base_type
	.long	.Linfo_string4          # DW_AT_name
	.byte	5                       # DW_AT_encoding
	.byte	4                       # DW_AT_byte_size
	.byte	10                      # Abbrev [10] 0xc5:0x5 DW_TAG_pointer_type
	.long	110                     # DW_AT_type
	.byte	14                      # Abbrev [14] 0xca:0x2a DW_TAG_subprogram
	.quad	.Lfunc_begin1           # DW_AT_low_pc
	.long	.Lfunc_end1-.Lfunc_begin1 # DW_AT_high_pc
	.byte	1                       # DW_AT_frame_base
	.byte	86
	.long	231                     # DW_AT_object_pointer
	.byte	1                       # DW_AT_decl_file
	.byte	1                       # DW_AT_decl_line
	.long	.Linfo_string12         # DW_AT_linkage_name
	.long	158                     # DW_AT_specification
	.byte	15                      # Abbrev [15] 0xe7:0xc DW_TAG_formal_parameter
	.byte	2                       # DW_AT_location
	.byte	145
	.byte	120
	.long	.Linfo_string18         # DW_AT_name
	.long	438                     # DW_AT_type
                                        # DW_AT_artificial
	.byte	0                       # End Of Children Mark
	.byte	5                       # Abbrev [5] 0xf4:0x3a DW_TAG_class_type
	.long	110                     # DW_AT_containing_type
	.long	.Linfo_string10         # DW_AT_name
	.byte	8                       # DW_AT_byte_size
	.byte	1                       # DW_AT_decl_file
	.byte	6                       # DW_AT_decl_line
	.byte	16                      # Abbrev [16] 0x100:0x7 DW_TAG_inheritance
	.long	110                     # DW_AT_type
	.byte	0                       # DW_AT_data_member_location
	.byte	1                       # DW_AT_accessibility
                                        # DW_ACCESS_public
	.byte	7                       # Abbrev [7] 0x107:0x1a DW_TAG_subprogram
	.long	.Linfo_string9          # DW_AT_linkage_name
	.long	.Linfo_string7          # DW_AT_name
	.byte	1                       # DW_AT_decl_file
	.byte	8                       # DW_AT_decl_line
	.byte	1                       # DW_AT_virtuality
	.byte	2                       # DW_AT_vtable_elem_location
	.byte	16
	.byte	0
                                        # DW_AT_declaration
                                        # DW_AT_external
	.byte	1                       # DW_AT_accessibility
                                        # DW_ACCESS_public
	.long	244                     # DW_AT_containing_type
	.byte	8                       # Abbrev [8] 0x11b:0x5 DW_TAG_formal_parameter
	.long	302                     # DW_AT_type
                                        # DW_AT_artificial
	.byte	0                       # End Of Children Mark
	.byte	9                       # Abbrev [9] 0x121:0xc DW_TAG_subprogram
	.long	.Linfo_string10         # DW_AT_name
                                        # DW_AT_declaration
                                        # DW_AT_artificial
                                        # DW_AT_external
	.byte	1                       # DW_AT_accessibility
                                        # DW_ACCESS_public
	.byte	8                       # Abbrev [8] 0x127:0x5 DW_TAG_formal_parameter
	.long	302                     # DW_AT_type
                                        # DW_AT_artificial
	.byte	0                       # End Of Children Mark
	.byte	0                       # End Of Children Mark
	.byte	10                      # Abbrev [10] 0x12e:0x5 DW_TAG_pointer_type
	.long	244                     # DW_AT_type
	.byte	14                      # Abbrev [14] 0x133:0x2a DW_TAG_subprogram
	.quad	.Lfunc_begin2           # DW_AT_low_pc
	.long	.Lfunc_end2-.Lfunc_begin2 # DW_AT_high_pc
	.byte	1                       # DW_AT_frame_base
	.byte	86
	.long	336                     # DW_AT_object_pointer
	.byte	1                       # DW_AT_decl_file
	.byte	6                       # DW_AT_decl_line
	.long	.Linfo_string13         # DW_AT_linkage_name
	.long	289                     # DW_AT_specification
	.byte	15                      # Abbrev [15] 0x150:0xc DW_TAG_formal_parameter
	.byte	2                       # DW_AT_location
	.byte	145
	.byte	120
	.long	.Linfo_string18         # DW_AT_name
	.long	443                     # DW_AT_type
                                        # DW_AT_artificial
	.byte	0                       # End Of Children Mark
	.byte	17                      # Abbrev [17] 0x15d:0x24 DW_TAG_subprogram
	.quad	.Lfunc_begin3           # DW_AT_low_pc
	.long	.Lfunc_end3-.Lfunc_begin3 # DW_AT_high_pc
	.byte	1                       # DW_AT_frame_base
	.byte	86
	.long	372                     # DW_AT_object_pointer
	.long	132                     # DW_AT_specification
	.byte	15                      # Abbrev [15] 0x174:0xc DW_TAG_formal_parameter
	.byte	2                       # DW_AT_location
	.byte	145
	.byte	120
	.long	.Linfo_string18         # DW_AT_name
	.long	438                     # DW_AT_type
                                        # DW_AT_artificial
	.byte	0                       # End Of Children Mark
	.byte	17                      # Abbrev [17] 0x181:0x24 DW_TAG_subprogram
	.quad	.Lfunc_begin4           # DW_AT_low_pc
	.long	.Lfunc_end4-.Lfunc_begin4 # DW_AT_high_pc
	.byte	1                       # DW_AT_frame_base
	.byte	86
	.long	408                     # DW_AT_object_pointer
	.long	263                     # DW_AT_specification
	.byte	15                      # Abbrev [15] 0x198:0xc DW_TAG_formal_parameter
	.byte	2                       # DW_AT_location
	.byte	145
	.byte	120
	.long	.Linfo_string18         # DW_AT_name
	.long	443                     # DW_AT_type
                                        # DW_AT_artificial
	.byte	0                       # End Of Children Mark
	.byte	10                      # Abbrev [10] 0x1a5:0x5 DW_TAG_pointer_type
	.long	426                     # DW_AT_type
	.byte	10                      # Abbrev [10] 0x1aa:0x5 DW_TAG_pointer_type
	.long	431                     # DW_AT_type
	.byte	13                      # Abbrev [13] 0x1af:0x7 DW_TAG_base_type
	.long	.Linfo_string16         # DW_AT_name
	.byte	6                       # DW_AT_encoding
	.byte	1                       # DW_AT_byte_size
	.byte	10                      # Abbrev [10] 0x1b6:0x5 DW_TAG_pointer_type
	.long	110                     # DW_AT_type
	.byte	10                      # Abbrev [10] 0x1bb:0x5 DW_TAG_pointer_type
	.long	244                     # DW_AT_type
	.byte	0                       # End Of Children Mark
	.section	.debug_ranges,"",@progbits
.Ldebug_ranges0:
	.quad	.Lfunc_begin0
	.quad	.Lfunc_end0
	.quad	.Lfunc_begin1
	.quad	.Lfunc_end1
	.quad	.Lfunc_begin2
	.quad	.Lfunc_end2
	.quad	.Lfunc_begin3
	.quad	.Lfunc_end3
	.quad	.Lfunc_begin4
	.quad	.Lfunc_end4
	.quad	0
	.quad	0
	.section	.debug_macinfo,"",@progbits
.Lcu_macro_begin0:
	.byte	0                       # End Of Macro List Mark
	.section	.debug_pubnames,"",@progbits
	.long	.LpubNames_end0-.LpubNames_begin0 # Length of Public Names Info
.LpubNames_begin0:
	.short	2                       # DWARF Version
	.long	.Lcu_begin0             # Offset of Compilation Unit Info
	.long	449                     # Compilation Unit Length
	.long	349                     # DIE offset
	.asciz	"Shape::draw"           # External Name
	.long	42                      # DIE offset
	.asciz	"main"                  # External Name
	.long	202                     # DIE offset
	.asciz	"Shape::Shape"          # External Name
	.long	385                     # DIE offset
	.asciz	"Rectangle::draw"       # External Name
	.long	307                     # DIE offset
	.asciz	"Rectangle::Rectangle"  # External Name
	.long	0                       # End Mark
.LpubNames_end0:
	.section	.debug_pubtypes,"",@progbits
	.long	.LpubTypes_end0-.LpubTypes_begin0 # Length of Public Types Info
.LpubTypes_begin0:
	.short	2                       # DWARF Version
	.long	.Lcu_begin0             # Offset of Compilation Unit Info
	.long	449                     # Compilation Unit Length
	.long	110                     # DIE offset
	.asciz	"Shape"                 # External Name
	.long	244                     # DIE offset
	.asciz	"Rectangle"             # External Name
	.long	190                     # DIE offset
	.asciz	"int"                   # External Name
	.long	176                     # DIE offset
	.asciz	"__vtbl_ptr_type"       # External Name
	.long	431                     # DIE offset
	.asciz	"char"                  # External Name
	.long	0                       # End Mark
.LpubTypes_end0:

	.ident	"clang version 6.0.0-1ubuntu2 (tags/RELEASE_600/final)"
	.section	".note.GNU-stack","",@progbits
	.section	.debug_line,"",@progbits
.Lline_table_start0:
