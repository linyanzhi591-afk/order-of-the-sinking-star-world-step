.intel_syntax noprefix
.text
.global world_delta_hook
world_delta_hook:
    pushfq
    push rax
    push rcx
    push rdx
    push r8
    push r9
    push r10
    push r11
    sub rsp, 0x80
    movups [rsp+0x20], xmm0
    movups [rsp+0x30], xmm1
    movups [rsp+0x40], xmm2
    movups [rsp+0x50], xmm3
    movups [rsp+0x60], xmm4
    movups [rsp+0x70], xmm5
    call world_filter
    movss [rsp+0x20], xmm0
    movups xmm0, [rsp+0x20]
    movups xmm1, [rsp+0x30]
    movups xmm2, [rsp+0x40]
    movups xmm3, [rsp+0x50]
    movups xmm4, [rsp+0x60]
    movups xmm5, [rsp+0x70]
    add rsp, 0x80
    pop r11
    pop r10
    pop r9
    pop r8
    pop rdx
    pop rcx
    pop rax
    popfq
    movss [rip+game_delta], xmm0
    jmp delta_return

.global world_gate_hook
world_gate_hook:
    /* 保留原比较的标志；暂停时不执行 delta=0 的逻辑更新。 */
    pushfq
    cmp DWORD PTR [rip+world_settings+8], 0
    jne paused_gate
    popfq
    jae positive_loop
    jmp after_loop
paused_gate:
    popfq
    ja positive_loop
    jmp after_loop
