# Lab 2: 物理内存管理

本实验主要在 uCore 中实现基本的物理内存管理，包括物理页分配和回收、二级页表的建立等。

由于 Lab 2 和 Lab 1 的代码有不少区别，添加了与内存管理相关的很多逻辑，于是首先从 bootloader 启动开始梳理了一遍 OS 启动流程。主要区别在于以下几点：

1. `boot/bootasm.S` 中，在进入保护模式之前对物理内存大小进行了探测，探测结果保存在物理内存 0x8000 处
2. kernel 的链接地址（也即 kernel 执行时指令中的虚拟地址）改为了 0xC0100000
3. `boot/bootmain.c` 将 kernel 加载到了物理地址 0x00100000，而不是直接使用 ELF 给出的 0xC0100000
4. kernel 的入口改为了 `kern/init/entry.S` 的 `kern_entry`

这里 `kern_entry` 相比 Lab 1 是完全新增的部分，主要功能是设置一个初始的页目录和页表，将虚拟地址 KERNBASE + (0 ~ 4M) 映射到物理地址 0 ~ 4M，并通知 CPU 启用页机制，然后调用 `kern/init/init.c` 的 `kern_init()`。

实验指导书里面「3.3.5 实现分页机制」这一部分内容和目前的代码已经严重脱节，可以说不具备参考意义了，这里直接通过理解视频课内容和阅读代码可以看明白做了什么，并在关键代码中加了中文注释。

`kern_init()` 中与本次实验相关的主要是 `pmm_init()` 函数的调用，进入了物理内存管理模块的初始化。

需要编码实现的部分主要有两个：物理页的管理、二级页表的建立。

## 管理物理页（实现 first-fit 连续物理内存分配算法）

这部分的一个关键函数是 `page_init()`，由 `pmm_init()` 调用。这个函数建立了用来表示整个物理内存的所有物理页的 `struct Page` 数组，并最终调用了 `pmm_manager` 的相关函数对各空闲物理内存块进行初始化。

为了实现对这些物理页（物理内存块）的管理，修改了 `kern/mm/default_pmm.c` 的 `default_init_memmap(base, n)`、`default_alloc_pages(n)`、`default_free_pages(base, n)` 三个函数，关键部分已加注释。

实现之后的效果是，`page_init()` 时，`default_pmm_manager` 将所有可用的内存块的起始页和内存块大小（页数）记录下来，随后向内核其它部分提供 `allow_page()` 和 `free_page()` 函数用来分配和释放物理页。

注意，这个练习里所实现的是物理页的分配，通过 `allow_page()` 申请时，是直接获得一个或连续的物理内存页。

## 建立二级页表

这部分所做的是建立虚拟地址到物理地址的映射。

实际上页目录还是复用了启动时的页目录位置，这里主要是实现了 `get_pte(pgdir, la, create` 和 `page_remove_pte(pgdir, la, ptep)` 两个函数。

`get_pte` 用于从线性地址（也就是虚拟地址，因为目前段机制实现的是对等映射）得到页表项（也就包含线性地址所映射到的物理地址），如果当前线性地址所对应的页表还不存在，则根据 `create` 参数来决定是否创建页表（需要申请一个物理页来存放该页表）。

`page_remove_pte` 用于将页表项删除，也就是删除一段虚拟地址（一个虚拟页）到物理地址（一个物理页）的映射。

修改的代码同样已经添加了注释。

## 参考资料

- [实验指导书 3.3 物理内存管理](https://objectkuan.gitbooks.io/ucore-docs/content/lab1/lab1_3_3_2_interrupt_exception.html)
- [Intel 80386 Programmer's Reference Manual](https://css.csail.mit.edu/6.858/2014/readings/i386.pdf), Chapter 5 Memory Management
