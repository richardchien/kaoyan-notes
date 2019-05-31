# Lab 1, Ex 1

为了观察效果，首先根据指导书运行了 `make "V="`。

这里 `"V="` 参数会使 make 程序打印所运行的所有命令，之所以如此是因为 Makefile 开头设置了 `V` 这个变量为 `@`（在命令开头加 `@` 会导致相应的命令本身不会被 make 输出），而从 make 命令的参数中传入的 `V=` 会将其置为空，也就使得执行的命令本身被输出。

然后结合 make 的输出，以及 Makefile 文件和相关源代码，可以看出主要做了下面这三件事情。

## 编译内核

Make 输出如下：

```
+ cc kern/init/init.c
gcc -Ikern/init/ -march=i686 -fno-builtin -fno-PIC -Wall -ggdb -m32 -gstabs -nostdinc  -fno-stack-protector -Ilibs/ -Ikern/debug/ -Ikern/driver/ -Ikern/trap/ -Ikern/mm/ -c kern/init/init.c -o obj/kern/init/init.o
kern/init/init.c:95:1: warning: ‘lab1_switch_test’ defined but not used [-Wunused-function]
  lab1_switch_test(void) {
  ^~~~~~~~~~~~~~~~
+ cc kern/libs/stdio.c
gcc -Ikern/libs/ -march=i686 -fno-builtin -fno-PIC -Wall -ggdb -m32 -gstabs -nostdinc  -fno-stack-protector -Ilibs/ -Ikern/debug/ -Ikern/driver/ -Ikern/trap/ -Ikern/mm/ -c kern/libs/stdio.c -o obj/kern/libs/stdio.o
+ cc kern/libs/readline.c
gcc -Ikern/libs/ -march=i686 -fno-builtin -fno-PIC -Wall -ggdb -m32 -gstabs -nostdinc  -fno-stack-protector -Ilibs/ -Ikern/debug/ -Ikern/driver/ -Ikern/trap/ -Ikern/mm/ -c kern/libs/readline.c -o obj/kern/libs/readline.o

...

+ ld bin/kernel
ld -m    elf_i386 -nostdlib -T tools/kernel.ld -o bin/kernel  obj/kern/init/init.o obj/kern/libs/stdio.o obj/kern/libs/readline.o obj/kern/debug/panic.o obj/kern/debug/kdebug.o obj/kern/debug/kmonitor.o obj/kern/driver/clock.o obj/kern/driver/console.o obj/kern/driver/picirq.o obj/kern/driver/intr.o obj/kern/trap/trap.o obj/kern/trap/vectors.o obj/kern/trap/trapentry.o obj/kern/mm/pmm.o  obj/libs/string.o obj/libs/printfmt.o
```

这部分首先编译了内核的源文件和某些必要函数库，生成的目标文件相应的在 `obj/kern` 和 `obj/libs`，然后链接相关目标文件，生成 `bin/kernel` 内核二进制文件。

Makefile 中相关部分如下：

```makefile
KINCLUDE += kern/debug/ \
            kern/driver/ \
            kern/trap/ \
            kern/mm/

KSRCDIR += kern/init \
           kern/libs \
           kern/debug \
           kern/driver \
           kern/trap \
           kern/mm

KCFLAGS += $(addprefix -I,$(KINCLUDE))

$(call add_files_cc,$(call listf_cc,$(KSRCDIR)),kernel,$(KCFLAGS))

KOBJS = $(call read_packet,kernel libs)

# create kernel target
kernel = $(call totarget,kernel)

$(kernel): tools/kernel.ld

$(kernel): $(KOBJS)
	@echo + ld $@
	$(V)$(LD) $(LDFLAGS) -T tools/kernel.ld -o $@ $(KOBJS)
	@$(OBJDUMP) -S $@ > $(call asmfile,kernel)
	@$(OBJDUMP) -t $@ | $(SED) '1,/SYMBOL TABLE/d; s/ .* / /; /^$$/d' > $(call symfile,kernel)

$(call create_target,kernel)
```

## 编译 BootLoader

Make 输出如下：

```
+ cc boot/bootasm.S
gcc -Iboot/ -march=i686 -fno-builtin -fno-PIC -Wall -ggdb -m32 -gstabs -nostdinc  -fno-stack-protector -Ilibs/ -Os -nostdinc -c boot/bootasm.S -o obj/boot/bootasm.o
+ cc boot/bootmain.c
gcc -Iboot/ -march=i686 -fno-builtin -fno-PIC -Wall -ggdb -m32 -gstabs -nostdinc  -fno-stack-protector -Ilibs/ -Os -nostdinc -c boot/bootmain.c -o obj/boot/bootmain.o
+ cc tools/sign.c
gcc -Itools/ -g -Wall -O2 -c tools/sign.c -o obj/sign/tools/sign.o
gcc -g -Wall -O2 obj/sign/tools/sign.o -o bin/sign
+ ld bin/bootblock
ld -m    elf_i386 -nostdlib -N -e start -Ttext 0x7C00 obj/boot/bootasm.o obj/boot/bootmain.o -o obj/bootblock.o
'obj/bootblock.out' size: 492 bytes
build 512 bytes boot sector: 'bin/bootblock' success!
```

对应的 Makefile 部分如下：

```makefile
# create bootblock
bootfiles = $(call listf_cc,boot)
$(foreach f,$(bootfiles),$(call cc_compile,$(f),$(CC),$(CFLAGS) -Os -nostdinc))

bootblock = $(call totarget,bootblock)

$(bootblock): $(call toobj,$(bootfiles)) | $(call totarget,sign)
	@echo + ld $@
	$(V)$(LD) $(LDFLAGS) -N -e start -Ttext 0x7C00 $^ -o $(call toobj,bootblock)
	@$(OBJDUMP) -S $(call objfile,bootblock) > $(call asmfile,bootblock)
	@$(OBJCOPY) -S -O binary $(call objfile,bootblock) $(call outfile,bootblock)
	@$(call totarget,sign) $(call outfile,bootblock) $(bootblock)

$(call create_target,bootblock)

# -------------------------------------------------------------------

# create 'sign' tools
$(call add_files_host,tools/sign.c,sign,sign)
$(call create_target_host,sign,sign)
```

这里首先编译了 `boot` 目录中的两个源文件，生成目标文件到 `obj/boot`。然后编译并链接了待会儿要用到的一个辅助工具 sign，生成可执行文件到 `bin/sign`。接着链接刚刚编译到 `obj/boot` 的两个目标文件，其中，`-e start` 参数指定了程序执行的入口，对应到 `boot/bootasm.S` 中的 `start` 标签；`-Ttext 0x7C00` 将代码段设置为从地址 `0x7C00` 开始。

链接生成的文件在 `obj/bootblock.o`，这个文件目前是 `elf32-i386` 格式，随后通过 `objcopy -S -O binary obj/bootblock.o obj/bootblock.out` 转换成了 `binary` 格式，也就是能直接在 CPU 上运行到原始二进制机器码。

再然后，利用刚刚编译的辅助工具 `bin/sign` 来将 `obj/bootblock.out` 转换成 `bin/bootblock`。具体地，参照 `tools/sign.c` 源文件，可以看到它的主要功能是读取 `obj/bootblock.out` 的内容，如果不足 510 字节，则在后面扩充 0，然后在结尾加上 `0x55 0xAA` 这两个字节（MBR 有效标志），再写入到 `bin/bootblock`。可见最终生成的 `bin/bootblock` 文件可以确定有 512 字节，且符合 MBR 的格式要求。去掉错误检查相关的代码，`tools/sign.c` 主要功能代码如下：

```c
char buf[512];
memset(buf, 0, sizeof(buf));
FILE *ifp = fopen(argv[1], "rb");
fread(buf, 1, st.st_size, ifp);
fclose(ifp);
buf[510] = 0x55;
buf[511] = 0xAA;
FILE *ofp = fopen(argv[2], "wb+");
fwrite(buf, 1, 512, ofp);
fclose(ofp);
```

## 生成 `ucore.img`

Make 输出如下：

```
dd if=/dev/zero of=bin/ucore.img count=10000
10000+0 records in
10000+0 records out
5120000 bytes (5.1 MB, 4.9 MiB) copied, 0.0432306 s, 118 MB/s
dd if=bin/bootblock of=bin/ucore.img conv=notrunc
1+0 records in
1+0 records out
512 bytes copied, 9.9966e-05 s, 5.1 MB/s
dd if=bin/kernel of=bin/ucore.img seek=1 conv=notrunc
154+1 records in
154+1 records out
```

Makefile 相关内容如下：

```makefile
# create ucore.img
UCOREIMG := $(call totarget,ucore.img)

$(UCOREIMG): $(kernel) $(bootblock)
	$(V)dd if=/dev/zero of=$@ count=10000
	$(V)dd if=$(bootblock) of=$@ conv=notrunc
	$(V)dd if=$(kernel) of=$@ seek=1 conv=notrunc

$(call create_target,ucore.img)
```

首先创建了一个 `5120000` 字节的全 0 文件，然后将 `bin/bootblock.out` 写入前 512 字节，再将 `bin/kernel` 写入从 512 字节开始之后的位置。这里所出现的「512」并没有在 Makefile 中显式指定，而是依赖于 `dd` 命令的 `obs` 参数的默认值。
