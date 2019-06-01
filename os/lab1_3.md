# Lab 1, Ex 3

分析 `boot/bootasm.S` 了解了 bootloader 从实模式切换到保护模式的过程。

## 初始设置

```s
cli               # Disable interrupts
cld               # String operations increment

# Set up the important data segment registers (DS, ES, SS).
xorw %ax, %ax     # Segment number zero
movw %ax, %ds     # -> Data Segment
movw %ax, %es     # -> Extra Segment
movw %ax, %ss     # -> Stack Segment
```

首先 `cli` 禁用中断，因为这时候还没有设置 IDT（中断描述符表），如果产生中断的话，CPU 将不能正确地找到相应的中断处理程序来处理。`cld` 是设置 x86 指令中字符串操作时的字符顺序，这里将其置零，即字符串操作时每个基本操作之后，将下标自增。

后面四行将 DS、ES、SS 初始化为 0。

## 使能 A20

```s
# Enable A20:
    #  For backwards compatibility with the earliest PCs, physical
    #  address line 20 is tied low, so that addresses higher than
    #  1MB wrap around to zero by default. This code undoes this.
seta20.1:
    inb $0x64, %al      # Wait for not busy(8042 input buffer empty).
    testb $0x2, %al
    jnz seta20.1

    movb $0xd1, %al     # 0xd1 -> port 0x64
    outb %al, $0x64     # 0xd1 means: write data to 8042's P2 port

seta20.2:
    inb $0x64, %al      # Wait for not busy(8042 input buffer empty).
    testb $0x2, %al
    jnz seta20.2

    movb $0xdf, %al     # 0xdf -> port 0x60
    outb %al, $0x60     # 0xdf = 11011111, means set P2's A20 bit(the 1 bit) to 1
```

根据实验指导书附录的「关于 A20 Gate」，在 8086 时代，由段+偏移机制所能产生的地址有 1088 KB，但地址线的物理寻址能力只有 1024 KB，当试图访问超过 1024 KB 的内存时，会发生「回卷」（wrap），而不会发生异常；但到了 80286，物理寻址能力已经提高，当访问超过 1 MB 的内存时不再发生回卷了，造成了不兼容，IBM PC 为了保持兼容性，加入了 A20 地址线的控制逻辑，并且大约是为了节省成本，这个控制逻辑被放在了键盘控制器中。A20 控制信号一开始是 0，表示屏蔽，也即保持兼容，在超过 1 MB 时「回卷」，为了利用完整的 32 位寻址能力，需要通过一系列 I/O 操作去改变键盘控制器中的相应控制信号。

`bootasm.S` 中的这部分代码有两阶段：第一阶段，向 8042 键盘控制器的 0x64 端口发送 0xD1 命令，表示要写 Output Port（因为 A20 控制信号在输出端口 P2 上）；第二阶段，向 0x60 端口（输入缓冲）发送要写入 Output Port 的内容，即 0xDF。

这里 0xDF 的二进制是 11011111，根据实验指导书和 OSDev Wiki 相关文档，其中第 1 bit 是 A20 使能信号，这里置为 1。但都没有提到其它位为什么这样设置。

于是在 `seta20.1` 之前加上了下面代码：

```s
    # Read the original value of 8042 Output Port.
reada20.1:
    inb $0x64, %al
    testb $0x2, %al
    jnz reada20.1
    movb $0xd0, %al
    outb %al, $0x64
reada20.2:
    inb $0x64, %al
    testb $0x2, %al
    jnz reada20.2
    inb $0x60, %al
```

通过单步调试查看这段代码之后 AL 的值，发现是 11001111，又把这段代码移到 `seta20.2` 后面，确实变成了我们所期望的 11011111，但这里变动的并不是第 1 bit（无论从低到高数还是从高到低数）。TODO：限于时间原因，暂时无法深究原因。

## 初始化 GDT（全局描述符表）

在保护模式中，逻辑地址（段选择子 + 偏移地址）转换为线性地址需要用到 GDT。CPU 首先从段选择子中取出高 12 位的描述符表索引值，然后从 GDT 中获取相应索引对应的段描述符，其中包含了段基址，加上偏移地址也就是线性地址。示意图如下：

![Segment Translation](images/segment-trans.png)

段描述符数据结构如下（对应了 `kern/mm/mmu.h` 中的 `struct segdesc` 结构体）：

![Segment-Descriptor Format](images/segment-descriptor-format.png)

段选择子（保护模式下，段寄存器所保存的内容）结构如下：

![Segment Selector](images/segment-selector.png)

了解了段式内存管理机制后，来看 `boot/bootasm.S` 加载 GDT 的代码：

```s
lgdt gdtdesc
```

直接使用了 `lgdt` 指令，`gdtdesc` 是一个标签（也就是一个地址），指向 `boot/bootasm.S` 结尾的内容：

```s
# Bootstrap GDT
.p2align 2                                    # force 4 byte alignment
gdt:
    SEG_NULLASM                               # null seg， selector: 0x0
    SEG_ASM(STA_X|STA_R, 0x0, 0xffffffff)     # code seg for bootloader and kernel, selector: 0x8
    SEG_ASM(STA_W, 0x0, 0xffffffff)           # data seg for bootloader and kernel, selector: 0x10

gdtdesc:
    .word 0x17                                # sizeof(gdt) - 1 (8*3-1 = 23 = 0x17)
    .long gdt                                 # address gdt
```

注意到，这里 `gdtdesc` 并不是真正的 GDT。真正的 GDT 是 `gdt` 标签所指向的内容，有三条记录（也就是三个段描述符），第一个是空，第二个是可读可执行的内核代码段，第三个是可写的内核数据段，根据之前的段描述符结构。每个描述符占 8 字节（64 位），因此三个段的段选择子分别是 0x0、0x8、0x10。

而 `gdtdesc` 是对 GDT 的描述（在 `libs/x86.h` 中由 `struct pseudodesc` 结构体表示，称为「伪描述符」），它包含了 GDT 的大小和地址（即 16 位的 limit 和 32 位的 base），当执行 `lgdt` 指令时，这个 limit 和 base 被放进了 GPTR 寄存器。

## 进入保护模式

加载 GDT 之后，使能并进入保护模式。代码如下：

```s
    movl %cr0, %eax
    orl $CR0_PE_ON, %eax
    movl %eax, %cr0

    # Jump to next instruction, but in 32-bit code segment.
    # Switches processor into 32-bit mode.
    ljmp $PROT_MODE_CSEG, $protcseg

.code32                           # Assemble for 32-bit mode
protcseg:
    # Set up the protected-mode data segment registers
    movw $PROT_MODE_DSEG, %ax     # Our data segment selector
    movw %ax, %ds                 # -> DS: Data Segment
    movw %ax, %es                 # -> ES: Extra Segment
    movw %ax, %fs                 # -> FS
    movw %ax, %gs                 # -> GS
    movw %ax, %ss                 # -> SS: Stack Segment

    # Set up the stack pointer and call into C. The stack region is from 0--start(0x7c00)
    movl $0x0, %ebp
    movl $start, %esp
    call bootmain
```

首先把 CR0 的值移到 EAX，然后将第 0 bit（保护模式使能位）置一，再放回，这时就开启了保护模式。接着使用 `ljmp` 长跳转指令，通过指定内核代码段，跳转到 `protcseg` 标签，同时也使 CS 寄存器值被正确地设置为分段机制下的内核代码段。

`protcseg` 中对各数据段寄存器进行了设置，这是已完成进入保护模式的所有工作。最后设置了 EBP 和 ESP，分别为栈帧基地址（这里为 0x0）和栈顶地址（这里为 0x7C00，栈是向内存低地址增长的，也就是说 PUSH 时 ESP 会减小），然后调用了 C 语言编写的 `bootmain` 函数，进入加载内核的过程。

## 参考资料

- [实验指导书 2.3.2.1 保护模式和分段机制](https://objectkuan.gitbooks.io/ucore-docs/content/lab1/lab1_3_2_1_protection_mode.html)
- [实验指导书 2.3.2.2 地址空间](https://objectkuan.gitbooks.io/ucore-docs/content/lab1/lab1_3_2_2_address_space.html)
- [实验指导书 2.5 关于 A20 Gate](https://objectkuan.gitbooks.io/ucore-docs/content/lab1/lab1_appendix_a20.html)
- [Intel 80386 Programmer's Reference Manual](https://css.csail.mit.edu/6.858/2014/readings/i386.pdf), Chapter 4 Systems Architecture, Chapter 5 Memory Management, Chapter 10 Initialization, Chapter 17 80386 Instruction Set
- ["8042" PS/2 Controller - OSDev Wiki](https://wiki.osdev.org/%228042%22_PS/2_Controller)
