	.text
	.file	"hello.c"
	.file	1 "/home/ssx/Desktop/reassessor/example" "src/hello.c"
	.globl	foo                     # -- Begin function foo
	.p2align	4, 0x90
	.type	foo,@function
foo:                                    # @foo
.Lfunc_begin0:
	.loc	1 5 0                   # src/hello.c:5:0
	.cfi_startproc
# %bb.0:
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset %rbp, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register %rbp
	movl	%edi, -4(%rbp)
.Ltmp0:
	.loc	1 6 10 prologue_end     # src/hello.c:6:10
	movl	-4(%rbp), %eax
	movl	%eax, %ecx
	movq	%rcx, %rdx
	subq	$3, %rdx
	movq	%rcx, -16(%rbp)         # 8-byte Spill
	.loc	1 6 3 is_stmt 0         # src/hello.c:6:3
	ja	.LBB0_5
# %bb.7:
	.loc	1 0 3                   # src/hello.c:0:3
	leaq	.LJTI0_0(%rip), %rax
	movq	-16(%rbp), %rcx         # 8-byte Reload
	movslq	(%rax,%rcx,4), %rdx
	addq	%rax, %rdx
	jmpq	*%rdx
.LBB0_1:
.Ltmp1:
	.loc	1 7 22 is_stmt 1        # src/hello.c:7:22
	movl	bar(%rip), %eax
	.loc	1 7 20 is_stmt 0        # src/hello.c:7:20
	movl	%eax, output(%rip)
	.loc	1 7 30                  # src/hello.c:7:30
	jmp	.LBB0_6
.LBB0_2:
	.loc	1 8 22 is_stmt 1        # src/hello.c:8:22
	movl	bar+4(%rip), %eax
	.loc	1 8 20 is_stmt 0        # src/hello.c:8:20
	movl	%eax, output(%rip)
	.loc	1 8 30                  # src/hello.c:8:30
	jmp	.LBB0_6
.LBB0_3:
	.loc	1 9 22 is_stmt 1        # src/hello.c:9:22
	movl	bar+8(%rip), %eax
	.loc	1 9 20 is_stmt 0        # src/hello.c:9:20
	movl	%eax, output(%rip)
	.loc	1 9 30                  # src/hello.c:9:30
	jmp	.LBB0_6
.LBB0_4:
	.loc	1 10 22 is_stmt 1       # src/hello.c:10:22
	movl	bar+12(%rip), %eax
	.loc	1 10 20 is_stmt 0       # src/hello.c:10:20
	movl	%eax, output(%rip)
	.loc	1 10 30                 # src/hello.c:10:30
	jmp	.LBB0_6
.LBB0_5:
	.loc	1 11 14 is_stmt 1       # src/hello.c:11:14
	jmp	.LBB0_6
.Ltmp2:
.LBB0_6:
	.loc	1 13 1                  # src/hello.c:13:1
	popq	%rbp
	.cfi_def_cfa %rsp, 8
	retq
.Ltmp3:
.Lfunc_end0:
	.size	foo, .Lfunc_end0-foo
	.cfi_endproc
	.section	.rodata,"a",@progbits
	.p2align	2
.LJTI0_0:
	.long	.LBB0_1-.LJTI0_0
	.long	.LBB0_2-.LJTI0_0
	.long	.LBB0_3-.LJTI0_0
	.long	.LBB0_4-.LJTI0_0
                                        # -- End function
	.text
	.globl	main                    # -- Begin function main
	.p2align	4, 0x90
	.type	main,@function
main:                                   # @main
.Lfunc_begin1:
	.loc	1 15 0                  # src/hello.c:15:0
	.cfi_startproc
# %bb.0:
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset %rbp, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register %rbp
	subq	$16, %rsp
	movl	$0, -4(%rbp)
.Ltmp4:
	.loc	1 17 9 prologue_end     # src/hello.c:17:9
	movl	-8(%rbp), %edi
	.loc	1 17 5 is_stmt 0        # src/hello.c:17:5
	callq	foo
.Ltmp5:
	.loc	1 18 11 is_stmt 1       # src/hello.c:18:11
	movl	$0, -8(%rbp)
.LBB1_1:                                # =>This Inner Loop Header: Depth=1
.Ltmp6:
	.loc	1 18 17 is_stmt 0       # src/hello.c:18:17
	cmpl	$4, -8(%rbp)
.Ltmp7:
	.loc	1 18 5                  # src/hello.c:18:5
	jge	.LBB1_4
# %bb.2:                                #   in Loop: Header=BB1_1 Depth=1
.Ltmp8:
	.loc	1 19 13 is_stmt 1       # src/hello.c:19:13
	movl	-8(%rbp), %edi
	.loc	1 19 9 is_stmt 0        # src/hello.c:19:9
	callq	foo
	.loc	1 20 49 is_stmt 1       # src/hello.c:20:49
	movl	-8(%rbp), %esi
	.loc	1 20 52 is_stmt 0       # src/hello.c:20:52
	movl	output(%rip), %edx
	.loc	1 20 9                  # src/hello.c:20:9
	leaq	.L.str(%rip), %rdi
	movb	$0, %al
	callq	printf@PLT
.Ltmp9:
# %bb.3:                                #   in Loop: Header=BB1_1 Depth=1
	.loc	1 18 22 is_stmt 1       # src/hello.c:18:22
	movl	-8(%rbp), %eax
	addl	$1, %eax
	movl	%eax, -8(%rbp)
	.loc	1 18 5 is_stmt 0        # src/hello.c:18:5
	jmp	.LBB1_1
.Ltmp10:
.LBB1_4:
	.loc	1 0 5                   # src/hello.c:0:5
	xorl	%eax, %eax
	.loc	1 22 5 is_stmt 1        # src/hello.c:22:5
	addq	$16, %rsp
	popq	%rbp
	.cfi_def_cfa %rsp, 8
	retq
.Ltmp11:
.Lfunc_end1:
	.size	main, .Lfunc_end1-main
	.cfi_endproc
                                        # -- End function
	.type	bar,@object             # @bar
	.section	.rodata,"a",@progbits
	.globl	bar
	.p2align	4
bar:
	.long	4294967088              # 0xffffff30
	.long	4294967072              # 0xffffff20
	.long	4294967056              # 0xffffff10
	.long	4294967040              # 0xffffff00
	.size	bar, 16

	.type	output,@object          # @output
	.comm	output,4,4
	.type	.L.str,@object          # @.str
	.section	.rodata.str1.1,"aMS",@progbits,1
.L.str:
	.asciz	"Hello World [In:%d, Out:%d]\n"
	.size	.L.str, 29

	.section	.debug_str,"MS",@progbits,1
.Linfo_string0:
	.asciz	"clang version 10.0.0-4ubuntu1 " # string offset=0
.Linfo_string1:
	.asciz	"src/hello.c"           # string offset=31
.Linfo_string2:
	.asciz	"/home/ssx/Desktop/reassessor/example" # string offset=43
.Linfo_string3:
	.asciz	"bar"                   # string offset=89
.Linfo_string4:
	.asciz	"int"                   # string offset=93
.Linfo_string5:
	.asciz	"__ARRAY_SIZE_TYPE__"   # string offset=97
.Linfo_string6:
	.asciz	"output"                # string offset=117
.Linfo_string7:
	.asciz	"foo"                   # string offset=124
.Linfo_string8:
	.asciz	"main"                  # string offset=128
.Linfo_string9:
	.asciz	"input"                 # string offset=133
.Linfo_string10:
	.asciz	"i"                     # string offset=139
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
	.byte	17                      # DW_AT_low_pc
	.byte	1                       # DW_FORM_addr
	.byte	18                      # DW_AT_high_pc
	.byte	6                       # DW_FORM_data4
	.byte	0                       # EOM(1)
	.byte	0                       # EOM(2)
	.byte	2                       # Abbreviation Code
	.byte	52                      # DW_TAG_variable
	.byte	0                       # DW_CHILDREN_no
	.byte	3                       # DW_AT_name
	.byte	14                      # DW_FORM_strp
	.byte	73                      # DW_AT_type
	.byte	19                      # DW_FORM_ref4
	.byte	63                      # DW_AT_external
	.byte	25                      # DW_FORM_flag_present
	.byte	58                      # DW_AT_decl_file
	.byte	11                      # DW_FORM_data1
	.byte	59                      # DW_AT_decl_line
	.byte	11                      # DW_FORM_data1
	.byte	2                       # DW_AT_location
	.byte	24                      # DW_FORM_exprloc
	.byte	0                       # EOM(1)
	.byte	0                       # EOM(2)
	.byte	3                       # Abbreviation Code
	.byte	1                       # DW_TAG_array_type
	.byte	1                       # DW_CHILDREN_yes
	.byte	73                      # DW_AT_type
	.byte	19                      # DW_FORM_ref4
	.byte	0                       # EOM(1)
	.byte	0                       # EOM(2)
	.byte	4                       # Abbreviation Code
	.byte	33                      # DW_TAG_subrange_type
	.byte	0                       # DW_CHILDREN_no
	.byte	73                      # DW_AT_type
	.byte	19                      # DW_FORM_ref4
	.byte	55                      # DW_AT_count
	.byte	11                      # DW_FORM_data1
	.byte	0                       # EOM(1)
	.byte	0                       # EOM(2)
	.byte	5                       # Abbreviation Code
	.byte	38                      # DW_TAG_const_type
	.byte	0                       # DW_CHILDREN_no
	.byte	73                      # DW_AT_type
	.byte	19                      # DW_FORM_ref4
	.byte	0                       # EOM(1)
	.byte	0                       # EOM(2)
	.byte	6                       # Abbreviation Code
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
	.byte	7                       # Abbreviation Code
	.byte	36                      # DW_TAG_base_type
	.byte	0                       # DW_CHILDREN_no
	.byte	3                       # DW_AT_name
	.byte	14                      # DW_FORM_strp
	.byte	11                      # DW_AT_byte_size
	.byte	11                      # DW_FORM_data1
	.byte	62                      # DW_AT_encoding
	.byte	11                      # DW_FORM_data1
	.byte	0                       # EOM(1)
	.byte	0                       # EOM(2)
	.byte	8                       # Abbreviation Code
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
	.byte	39                      # DW_AT_prototyped
	.byte	25                      # DW_FORM_flag_present
	.byte	63                      # DW_AT_external
	.byte	25                      # DW_FORM_flag_present
	.byte	0                       # EOM(1)
	.byte	0                       # EOM(2)
	.byte	9                       # Abbreviation Code
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
	.byte	10                      # Abbreviation Code
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
	.byte	11                      # Abbreviation Code
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
	.byte	0                       # EOM(3)
	.section	.debug_info,"",@progbits
.Lcu_begin0:
	.long	.Ldebug_info_end0-.Ldebug_info_start0 # Length of Unit
.Ldebug_info_start0:
	.short	4                       # DWARF version number
	.long	.debug_abbrev           # Offset Into Abbrev. Section
	.byte	8                       # Address Size (in bytes)
	.byte	1                       # Abbrev [1] 0xb:0xb5 DW_TAG_compile_unit
	.long	.Linfo_string0          # DW_AT_producer
	.short	12                      # DW_AT_language
	.long	.Linfo_string1          # DW_AT_name
	.long	.Lline_table_start0     # DW_AT_stmt_list
	.long	.Linfo_string2          # DW_AT_comp_dir
	.quad	.Lfunc_begin0           # DW_AT_low_pc
	.long	.Lfunc_end1-.Lfunc_begin0 # DW_AT_high_pc
	.byte	2                       # Abbrev [2] 0x2a:0x15 DW_TAG_variable
	.long	.Linfo_string3          # DW_AT_name
	.long	63                      # DW_AT_type
                                        # DW_AT_external
	.byte	1                       # DW_AT_decl_file
	.byte	3                       # DW_AT_decl_line
	.byte	9                       # DW_AT_location
	.byte	3
	.quad	bar
	.byte	3                       # Abbrev [3] 0x3f:0xc DW_TAG_array_type
	.long	75                      # DW_AT_type
	.byte	4                       # Abbrev [4] 0x44:0x6 DW_TAG_subrange_type
	.long	87                      # DW_AT_type
	.byte	4                       # DW_AT_count
	.byte	0                       # End Of Children Mark
	.byte	5                       # Abbrev [5] 0x4b:0x5 DW_TAG_const_type
	.long	80                      # DW_AT_type
	.byte	6                       # Abbrev [6] 0x50:0x7 DW_TAG_base_type
	.long	.Linfo_string4          # DW_AT_name
	.byte	5                       # DW_AT_encoding
	.byte	4                       # DW_AT_byte_size
	.byte	7                       # Abbrev [7] 0x57:0x7 DW_TAG_base_type
	.long	.Linfo_string5          # DW_AT_name
	.byte	8                       # DW_AT_byte_size
	.byte	7                       # DW_AT_encoding
	.byte	2                       # Abbrev [2] 0x5e:0x15 DW_TAG_variable
	.long	.Linfo_string6          # DW_AT_name
	.long	80                      # DW_AT_type
                                        # DW_AT_external
	.byte	1                       # DW_AT_decl_file
	.byte	2                       # DW_AT_decl_line
	.byte	9                       # DW_AT_location
	.byte	3
	.quad	output
	.byte	8                       # Abbrev [8] 0x73:0x24 DW_TAG_subprogram
	.quad	.Lfunc_begin0           # DW_AT_low_pc
	.long	.Lfunc_end0-.Lfunc_begin0 # DW_AT_high_pc
	.byte	1                       # DW_AT_frame_base
	.byte	86
	.long	.Linfo_string7          # DW_AT_name
	.byte	1                       # DW_AT_decl_file
	.byte	5                       # DW_AT_decl_line
                                        # DW_AT_prototyped
                                        # DW_AT_external
	.byte	9                       # Abbrev [9] 0x88:0xe DW_TAG_formal_parameter
	.byte	2                       # DW_AT_location
	.byte	145
	.byte	124
	.long	.Linfo_string9          # DW_AT_name
	.byte	1                       # DW_AT_decl_file
	.byte	5                       # DW_AT_decl_line
	.long	80                      # DW_AT_type
	.byte	0                       # End Of Children Mark
	.byte	10                      # Abbrev [10] 0x97:0x28 DW_TAG_subprogram
	.quad	.Lfunc_begin1           # DW_AT_low_pc
	.long	.Lfunc_end1-.Lfunc_begin1 # DW_AT_high_pc
	.byte	1                       # DW_AT_frame_base
	.byte	86
	.long	.Linfo_string8          # DW_AT_name
	.byte	1                       # DW_AT_decl_file
	.byte	14                      # DW_AT_decl_line
	.long	80                      # DW_AT_type
                                        # DW_AT_external
	.byte	11                      # Abbrev [11] 0xb0:0xe DW_TAG_variable
	.byte	2                       # DW_AT_location
	.byte	145
	.byte	120
	.long	.Linfo_string10         # DW_AT_name
	.byte	1                       # DW_AT_decl_file
	.byte	16                      # DW_AT_decl_line
	.long	80                      # DW_AT_type
	.byte	0                       # End Of Children Mark
	.byte	0                       # End Of Children Mark
.Ldebug_info_end0:
	.ident	"clang version 10.0.0-4ubuntu1 "
	.section	".note.GNU-stack","",@progbits
	.addrsig
	.addrsig_sym foo
	.addrsig_sym printf
	.addrsig_sym bar
	.addrsig_sym output
	.section	.debug_line,"",@progbits
.Lline_table_start0:
