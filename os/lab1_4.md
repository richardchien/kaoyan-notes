# Lab 1, Ex 4: 分析 bootloader 加载 ELF 格式的 OS 内核的过程

通过分析 `boot/bootmain.c` 了解了 bootloader 加载内核程序的过程。

下面是其主要代码（由 `boot/bootasm.S` 在进入保护模式后调用）：

```c
/* bootmain - the entry of bootloader */
void
bootmain(void) {
    // read the 1st page off disk
    readseg((uintptr_t)ELFHDR, SECTSIZE * 8, 0);

    // is this a valid ELF?
    if (ELFHDR->e_magic != ELF_MAGIC) {
        goto bad;
    }

    struct proghdr *ph, *eph;

    // load each program segment (ignores ph flags)
    ph = (struct proghdr *)((uintptr_t)ELFHDR + ELFHDR->e_phoff);
    eph = ph + ELFHDR->e_phnum;
    for (; ph < eph; ph ++) {
        readseg(ph->p_va & 0xFFFFFF, ph->p_memsz, ph->p_offset);
    }

    // call the entry point from the ELF header
    // note: does not return
    ((void (*)(void))(ELFHDR->e_entry & 0xFFFFFF))();

bad:
    outw(0x8A00, 0x8A00);
    outw(0x8A00, 0x8E00);

    /* do nothing */
    while (1);
}
```

## 读取 ELF 头部

首先调用 `readseg(va, count, offset)` 函数从磁盘偏移 0 处读取了 8 个扇区到 `ELFHDR` 结构体。这里有两点。

首先，偏移 0 并不是真的从磁盘的第 0 扇区开始读。查看 `readseg(va, count, offset)` 函数源码：

```c
/* *
 * readseg - read @count bytes at @offset from kernel into virtual address @va,
 * might copy more than asked.
 * */
static void
readseg(uintptr_t va, uint32_t count, uint32_t offset) {
    uintptr_t end_va = va + count;

    // round down to sector boundary
    va -= offset % SECTSIZE;

    // translate from bytes to sectors; kernel starts at sector 1
    uint32_t secno = (offset / SECTSIZE) + 1;

    // If this is too slow, we could read lots of sectors at a time.
    // We'd write more to memory than asked, but it doesn't matter --
    // we load in increasing order.
    for (; va < end_va; va += SECTSIZE, secno ++) {
        readsect((void *)va, secno);
    }
}
```

可以发现它在从 `offset` 计算 `secno` 的时候，在最后加了 1，因为 bootloader 在第 0 扇区，这里为了在 `bootmain()` 中只需要考虑 `bin/kernel` 的结构，隐藏了这个细节。

第二，`ELFHDR` 是一个宏，本质上是 `((struct elfhdr *)0x10000)`，实际就是直接把虚拟地址 0x10000 看作了一个 `struct elfhdr` 指针。

于是，`readseg((uintptr_t)ELFHDR, SECTSIZE * 8, 0)` 把磁盘的 1～8 扇区读取到了内存的 0x10000 地址处。

查看 ELF 的格式说明可以看到，ELF 主头部占了 52 字节（0x34），之后的的内容是程序头部（Program Header）。在 GDB 中打印 `ELFHDR->e_phnum` 可以看到内核 ELF 中包含了 3 个程序头部，再查看 `bin/kernel` 的二进制内容可以发现，在 0x34 地址（ELF 头部的结尾）之后确实还有一部分非零内容，之后一直到 0x1000（第 4096 字节）全都是 0。

ELF 头部读取完成后，通过比对 `ELFHDR->e_magic` 验证了 ELF 格式是否有效。

这时候在 GDB 打印 0x10000 地址的内存数据可以看到 ELF 头部确实已经在这里：

![Kernel ELF Header in Memory](images/lab1/kernel-elf-hdr-in-mem.png)

## 读取程序段（Program Segment）

之前已经读取了开头的 8 个扇区，里面包含了所有程序头部。于是现在根据 ELF 头部的相关信息（`ELFHDR->e_phoff` 和 `ELFHDR->e_phnum`）来遍历地将内核的所有程序段读入内存。

在 GDB 中跟踪了第一个程序段读取的过程。首先，`ph->p_offset` 值为 0x1000，显然这就是 `bin/kernel` 开头 8 个扇区结束后的地址；`ph->p_va` 值为 0x100000，这是读取的目标地址。因此 `readseg(ph->p_va & 0xFFFFFF, ph->p_memsz, ph->p_offset)` 把内核 0x1000 处开始的 `ph->p_memsz` 个字节的程序段读取到了内存的 0x100000 地址处。

后续的另外两个程序段也类似。

## 启动内核

`bootmain()` 函数的结尾将 `ELFHDR->e_entry` 转换为函数指针然后调用，也就是真正地启动了内核。这里 `ELFHDR->e_entry` 的值为 0x100000，也就是刚刚加载的第一个程序段所在的内存地址。

进一步观察 `obj/kernel.asm` 文件可以发现 `kern_init()` 函数的装载地址被配置为 0x100000：

```c
int
kern_init(void) {
  100000:	55                   	push   %ebp
  100001:	89 e5                	mov    %esp,%ebp
  100003:	83 ec 28             	sub    $0x28,%esp
    extern char edata[], end[];
    memset(edata, 0, end - edata);
...
```

而这个 0x100000 地址是在链接器脚本 `tools/kernel.ld` 中指定的：

```
/* Load the kernel at this address: "." means the current address */
. = 0x100000;
```

尝试将 `tools/kernel.ld` 中的 0x100000 改为 0x101000，可以预期：`bin/kernel` 中第一个程序段仍然在 0x1000 位置，ELF 头部仍然加载到了内存的 0x10000 地址处，而 `kern_init()` 函数在内存中的位置（也就是内核的第一个程序段在内存中的起始位置）应该变为 0x101000。最终结果也确实如此：

![Kernel Entry at 0x101000](images/lab1/kernel_entry_at_0x101000.png)

## 参考资料

- [实验指导书 2.3.2.3 硬盘访问概述](https://objectkuan.gitbooks.io/ucore-docs/content/lab1/lab1_3_2_3_dist_accessing.html)
- [实验指导书 2.3.2.3 ELF 文件格式概述](https://objectkuan.gitbooks.io/ucore-docs/content/lab1/lab1_3_2_4_elf.html)
- [ELF - OSDev Wiki](https://wiki.osdev.org/ELF)
