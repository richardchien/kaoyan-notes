# Lab 3: 虚拟内存管理

本实验实现了基本的虚拟内存管理，包括缺页异常处理和换页机制（页置换算法）。

首先是阅读实验指导书和相关文档，理解了 uCore 中虚拟内存管理所需要做的事情，主要有下面几点：

- 物理内存管理实现了连续的物理页的分配，虚拟内存管理则是实现对进程隐藏物理内存管理的细节，实现以页为单位按需加载内容到内存（而无需进程知晓）
- 一个进程的虚拟地址空间的有效范围和页目录等，由一个 `struct mm_struct` 表示
- 当进程访问的虚拟地址合法，且当前并不存在于物理内存中时，CPU 产生缺页异常，在 `kern/mm/vmm.c` 的 `do_pgfault(mm, error_code, addr)` 中需要给这个虚拟地址分配一个对应的物理页，如果曾经被换出，还需要将页面换入
- FIFO 页置换算法需要维护一个按分配顺序排列的物理页队列，也就是说需要在初次分配、换入、换出时，分别将物理页插入队尾和取出队首物理页

## 实现缺页时分配物理页

练习 1 比较简单，就是在发生缺页异常时，为产生缺页的线性地址分配一个物理页，并在页表中建立一个映射。此时无需关心这个页的换入换出问题。

于是 `do_pgfault` 函数补充代码如下：

```c
ptep = get_pte(mm->pgdir, addr, 1);
if (*ptep == 0) { // 当前访问的线性地址在当前页目录中还没有建立映射
    struct Page *page = pgdir_alloc_page(mm->pgdir, addr, perm); // 则直接分配物理内存并建立映射
    if (page == NULL) {
        goto failed;
    }
}
```

实际上 `pgdir_alloc_page(pgdir, addr, perm)` 做了大部分事情，包括分配物理页、建立映射、标记可交换。

## 实现 FIFO 页置换机制

练习 2 的页置换机制涉及到三个地方，分别是 `swap_map_swappable`、`swap_out_victim`、`do_pgfault` 三个函数。

基本上注释都给出了具体思路，每个函数只需要一两行代码。

`swap_map_swappable` 函数把物理页标记为可交换，对于 FIFO 算法来说，也就是把物理页放到分配顺序队列的队尾。具体实现在 `_fifo_map_swappable`，代码如下：

```c
/*
 * (3)_fifo_map_swappable: According FIFO PRA, we should link the most recent arrival page at the back of pra_list_head qeueue
 */
static int
_fifo_map_swappable(struct mm_struct *mm, uintptr_t addr, struct Page *page, int swap_in)
{
    list_entry_t *head=(list_entry_t*) mm->sm_priv;
    list_entry_t *entry=&(page->pra_page_link);

    assert(entry != NULL && head != NULL);
    //record the page access situlation
    /*LAB3 EXERCISE 2: YOUR CODE*/
    //(1)link the most recent arrival page at the back of the pra_list_head qeueue.
    list_add_before(head, entry); // 将刚刚换入到的物理页加到最近访问列表的尾部
    return 0;
}
```

`swap_out_victim` 函数则是把队头的物理页（最早分配的物理页）返回，作为要换出的页。具体实现在 `_fifo_swap_out_victim` 函数，代码如下：

```c
/*
 *  (4)_fifo_swap_out_victim: According FIFO PRA, we should unlink the  earliest arrival page in front of pra_list_head qeueue,
 *                            then assign the value of *ptr_page to the addr of this page.
 */
static int
_fifo_swap_out_victim(struct mm_struct *mm, struct Page ** ptr_page, int in_tick)
{
    list_entry_t *head=(list_entry_t*) mm->sm_priv;
    assert(head != NULL);
    assert(in_tick==0);
    /* Select the victim */
    /*LAB3 EXERCISE 2: YOUR CODE*/
    //(1)  unlink the  earliest arrival page in front of pra_list_head qeueue
    //(2)  assign the value of *ptr_page to the addr of this page

    list_entry_t *victim = list_next(&pra_list_head);
    if (victim == &pra_list_head) {
        return 1; // FIFO 队列里没有元素, 也就是没有最近使用的物理页
    }

    list_del(victim);
    *ptr_page = le2page(victim, pra_page_link);
    return 0;
}
```

`do_pgfault` 函数需要在练习 1 的基础上再加上 else 语句，对于之前分配物理页后被换出的页，需要再次换入，并建立正确映射，且标记为可交换，如下：

```c
ptep = get_pte(mm->pgdir, addr, 1);
if (*ptep == 0) { // 当前访问的线性地址在当前页目录中还没有建立映射
    struct Page *page = pgdir_alloc_page(mm->pgdir, addr, perm); // 则直接分配物理内存并建立映射
    if (page == NULL) {
        goto failed;
    }
} else { // 当前访问的线性地址曾经建立过映射, 但被换出到了硬盘, 此时 *ptep 是一个 swap_entry_t
    if (swap_init_ok) {
        struct Page *page = NULL;
        swap_in(mm, addr, &page);
        page_insert(mm->pgdir, page, addr, perm); // 重新建立页表映射
        swap_map_swappable(mm, addr, page, 0); // 设置该物理页为可交换
        page->pra_vaddr = addr;
    } else {
        cprintf("no swap_init_ok but ptep is %x, failed\n", *ptep);
        goto failed;
    }
}
```

## 参考资料

- [实验指导书 4.3 虚拟内存管理](https://objectkuan.gitbooks.io/ucore-docs/content/lab3/lab3_3_vmm.html)
- [实验指导书 4.4 Page Fault 异常处理](https://objectkuan.gitbooks.io/ucore-docs/content/lab3/lab3_4_page_fault_handler.html)
- [实验指导书 4.5 页面置换机制的实现](https://objectkuan.gitbooks.io/ucore-docs/content/lab3/lab3_5_swapping.html)
- [Intel 80386 Programmer's Reference Manual](https://css.csail.mit.edu/6.858/2014/readings/i386.pdf), Chapter 5 Memory Management
