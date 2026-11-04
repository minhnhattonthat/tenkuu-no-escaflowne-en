; vwf.asm: proportional ASCII text and two-letter codes for the game's one text interpreter (docs/re/engine.md).
; armips -strequ EXE <copy of SLPS_010.15> -strequ FONT <font blob> -strequ DTE <pair table> asm/vwf.asm
;
; A byte below 0x80 reaches 0x8003AE14. Inside a name tag an ASCII digit still means the original portrait id; every
; other such byte is now a character. Bytes 01-1F (not 0A) and A0-DF draw two characters from a table: no string uses
; them, and script blocks can't grow in chapters 4 and 7 (docs/re/free-space.md).
;
; The pen is in pixels; w+0x36 stays the pen in VRAM words, rounded up, so the engine's newline, wrap and menu-mark code
; keep working untouched. Registers: this is -O0 code, nothing lives in a register across statements, and $ra was saved
; in the prologue, so t0-t9, a0-a3, v0, v1, at and ra are all free here.
;
; Room (docs/re/free-space.md): the original renderer shrinks to make room for the font, and the hook takes an unused run
; in the EXE's data and libgpu's debug strings. Most zero runs in this EXE are live images, so don't guess: trap-test.

.psx
.open EXE, 0x8000F800

; spare bytes in each window's second glyph buffer: a glyph uses at most 128 of its 0x200 (docs/re/engine.md)
W_PEN   equ 0x4C0   ; u16 pen in pixels
W_INK   equ 0x4C2   ; u16 ink colour of the last glyph
W_PEND  equ 0x4C4   ; u8 second character of a pair, not drawn yet
W_CARRY equ 0x4C8   ; 16 bytes: per row, the pixels already drawn in the word the pen is inside

GLYPH_TOP equ 2     ; first of the cell's 16 rows that holds font row 0
FONT_ROWS equ 12

KROM       equ 0x8007B018   ; Krom2RawAdd: Shift-JIS code -> 15 rows of 2 bytes in the BIOS font, or -1
LOAD_IMAGE equ 0x80063A7C
DRAW_SYNC  equ 0x800637B8
RESUME     equ 0x8003AF1C   ; after the opcode switch: the next state check
DIGITS     equ 0x8003AE1C   ; the original 2-digit parse, one instruction into it
TWO_BYTE   equ 0x8003A44C   ; the original 2-byte path, past the two instructions the jump replaced

.org 0x8003A444             ; bit 7 set. Was: lhu v1,0x2E(fp) / nop
    j     vwf_high
    nop

.org 0x8003AE14             ; bit 7 clear. Was: lhu v0,0x2E(fp) / nop
    j     vwf_low
    nop

; --- the Shift-JIS renderer: a0 = code, a1 = w+0xC4, a2 = buffer, returns a2. Pixel-equal to the routine it replaces
; (tests/test_vwf.py), minus the bold flags no string sets. Followed by the font, in the room that leaves.
.org 0x80039AD4
.area 0x8003A1A8 - 0x80039AD4
sjis_glyph:
    addiu sp, sp, -0x18
    sw    ra, 0x14(sp)
    sw    s0, 0x10(sp)
    sw    s1, 0x0C(sp)
    move  s0, a1
    move  s1, a2
    sh    zero, W_PEN - 0xC4(s0) ; the next ASCII glyph follows w+0x36: a stale pen can round to it and draw its old carry
    jal   KROM
    andi  a0, a0, 0xFFFF
    move  t9, v0                ; t9 = font rows, or -1
    lhu   t0, 0(s0)
    lhu   t1, 2(s0)
    lhu   t2, 4(s0)
    lhu   t3, 6(s0)
    andi  t0, t0, 0x8000        ; t0 != 0: squeeze 16 columns to 12
    andi  t1, t1, 0xF           ; ink
    andi  t2, t2, 0xF           ; background
    andi  t3, t3, 0xF           ; shadow
    move  t4, s1
    move  t6, zero              ; t6 = previous row's ink
    li    v1, 16                ; v1 = rows left
@@row:
    move  t7, zero
    slti  at, v1, 2             ; the 16th row has no font data
    bnez  at, @@have
    nop
    addiu at, t9, 1
    beqz  at, @@have
    nop
    lbu   t7, 0(t9)
    lbu   at, 1(t9)
    addiu t9, t9, 2
    sll   t7, t7, 8
    or    t7, t7, at
    beqz  t0, @@have
    nop
    andi  at, t7, 0xC000
    andi  t8, t7, 0x3C00
    sll   t8, t8, 1
    or    at, at, t8
    andi  t8, t7, 0x03C0
    sll   t8, t8, 2
    or    at, at, t8
    andi  t8, t7, 0x003C
    sll   t8, t8, 3
    or    at, at, t8
    andi  t8, t7, 0x0003
    sll   t8, t8, 4
    or    t7, at, t8
@@have:
    sll   t5, t7, 16
    andi  at, t6, 0xFFFF
    or    t5, t5, at
    move  t6, t7
    bnez  t0, @@bytes
    li    t8, 6
    li    t8, 8
@@bytes:
    bltz  t5, @@left
    move  a0, t1
    sll   at, t5, 16
    bltz  at, @@left
    move  a0, t3
    move  a0, t2
@@left:
    sll   at, t5, 1
    bltz  at, @@right
    move  at, t1
    sll   at, t5, 17
    bltz  at, @@right
    move  at, t3
    move  at, t2
@@right:
    sll   at, at, 4
    or    a0, a0, at
    sb    a0, 0(t4)
    addiu t4, t4, 1
    sll   t5, t5, 2
    addiu t8, t8, -1
    bgtz  t8, @@bytes
    nop
    addiu v1, v1, -1
    bgtz  v1, @@row
    nop
    move  v0, s1
    lw    ra, 0x14(sp)
    lw    s0, 0x10(sp)
    lw    s1, 0x0C(sp)
    jr    ra
    addiu sp, sp, 0x18

glyph_data:   ; armips symbols ignore case: this can't be called "font"
.incbin FONT
.endarea

; --- the hook, part 1: decode the byte, find the pen, wrap
.org 0x80010254
.area 0x800104AC - 0x80010254
vwf_high:
    lhu   v1, 0x2E(fp)
    nop
    addiu at, v1, -0xA0
    sltiu at, at, 0x40
    bnez  at, @@pair_high
    nop
    j     TWO_BYTE
    nop
@@pair_high:
    b     vwf_pair
    addiu t1, v1, 0x20 - 0xA0   ; table slot: 00-1F, then A0-DF

vwf_low:
    lhu   t1, 0x2E(fp)
    lw    t0, 0x60(fp)
    sltiu at, t1, 0x20
    bnez  at, vwf_pair
    nop
    lh    t2, 0xCC(t0)          ; -1 inside a name tag
    addiu t3, t1, -0x30
    bgez  t2, vwf_single
    sltiu t3, t3, 10
    beqz  t3, vwf_single
    nop
    lhu   v0, 0x2E(fp)
    j     DIGITS
    nop

vwf_single:
    move  t2, zero              ; t1 = character, t2 = second character or 0
    b     vwf_start
    nop

vwf_pair:
    sll   t1, t1, 1
    la    t2, dte_table
    addu  t2, t2, t1
    lbu   t1, 0(t2)
    lbu   t2, 1(t2)
    lw    t0, 0x60(fp)
    nop                         ; load delay: vwf_start reads t0 at once

vwf_start:
    sb    t2, W_PEND(t0)
    addiu t1, t1, -0x20
    sltiu at, t1, 95
    bnez  at, @@known
    nop
    li    t1, '?' - 0x20
@@known:
    la    t6, glyph_data
    addu  t7, t6, t1
    lbu   t3, 0(t7)             ; t3 = advance of the first character
    beqz  t2, @@measured
    move  t7, zero              ; t7 = advance of the second (t2 is a character, always a known one: tools/dte.py)
    addu  t7, t6, t2
    lbu   t7, -0x20(t7)
@@measured:
    lh    t4, 0x36(t0)
    lhu   t5, W_PEN(t0)         ; t5 = pen
    bnez  t4, @@line_started    ; every line start zeroes w+0x36, so nothing else has to reset the pen
    nop
    b     @@pen_known
    move  t5, zero
@@line_started:
    addiu t6, t5, 3
    srl   t6, t6, 2
    beq   t6, t4, @@pen_known   ; a Shift-JIS glyph since the last ASCII one moved w+0x36: follow it
    nop
    sll   t5, t4, 2
@@pen_known:
    lhu   t6, 0xC6(t0)
    lhu   t4, W_INK(t0)
    sh    t6, W_INK(t0)
    beq   t6, t4, @@same_ink
    nop
    addiu t5, t5, 3             ; a new colour starts a new word, or the carried pixels would change colour too
    srl   t5, t5, 2
    sll   t5, t5, 2
@@same_ink:
    lh    t6, 0x30(t0)
    addu  t7, t7, t3
    addiu t7, t7, -1
    addu  t7, t7, t5
    sll   t6, t6, 2
    slt   t7, t6, t7            ; line limit < pen + width?
    beqz  t7, @@draw
    nop
    beqz  t5, @@draw
    nop
    lw    t7, 0x40(t0)          ; wrap: the newline state runs, then this byte is read again
    li    t6, 5
    addiu t7, t7, -1
    sw    t7, 0x40(t0)
    sh    t6, 0x34(t0)
    sb    zero, W_PEND(t0)
    j     RESUME
    nop
@@draw:
    j     vwf_glyph
    nop

; part 3: upload the glyph, commit the pen, draw the pair's second character. a3 = bytes per row, t2 = buffer's end
vwf_finish:
    lhu   at, 0x2C(t0)          ; the RECT, in the interpreter's own local (LoadImage copies it)
    srl   t6, t5, 2
    addu  at, at, t6
    sh    at, 0x30(fp)
    lhu   at, 0x2E(t0)
    lhu   t6, 0x38(t0)
    nop
    addu  at, at, t6
    sh    at, 0x32(fp)
    srl   at, a3, 1
    sh    at, 0x34(fp)
    li    at, 16
    sh    at, 0x36(fp)
    addu  t5, t5, t3
    sh    t5, W_PEN(t0)
    addiu at, t5, 3
    srl   at, at, 2
    sh    at, 0x36(t0)
    li    at, 1                 ; what the original path does after a glyph
    sh    at, 0xD6(t0)
    lw    t6, 0x170(gp)
    nop
    addiu t6, t6, 1
    sw    t6, 0x170(gp)
    lui   t6, 0x800A
    sw    at, -0x5190(t6)
    addiu a0, fp, 0x30
    sll   at, a3, 4
    jal   LOAD_IMAGE
    subu  a1, t2, at
    lw    t0, 0x60(fp)
    nop
    lbu   t1, W_PEND(t0)
    nop
    bnez  t1, @@second
    nop
    ; state 3 runs the original pacing, then state 4 adds the cell's words to w+0x36 and starts a new line if it's full
    lhu   at, 0xC4(t0)
    lh    t6, 0x36(t0)
    andi  at, at, 0x8000
    bnez  at, @@cell_known
    addiu t6, t6, -3
    addiu t6, t6, -1
@@cell_known:
    sh    t6, 0x36(t0)
    li    at, 3
    sh    at, 0x34(t0)
    j     RESUME
    nop
@@second:
    sb    zero, W_PEND(t0)
    la    t6, glyph_data - 0x20
    addu  t6, t6, t1
    lbu   t3, 0(t6)
    lhu   t5, W_PEN(t0)
    j     vwf_glyph
    addiu t1, t1, -0x20
.endarea

; --- part 2: one glyph into a buffer. t0 = window, t1 = glyph index, t3 = advance, t5 = pen
.org 0x80011C28             ; over libgpu's debug format strings. All but one are gated at debug level >= 2. ResetGraph:jtb (0x80011D2C)
                            ; prints at ResetGraph(0): tests/test_romdiff.py keeps that address free of %
.area 0x80011F50 - 0x80011C28
vwf_glyph:
    lh    at, 0x1E(fp)          ; two buffers, then wait for their uploads: same as the original
    nop
    slti  at, at, 2
    bnez  at, @@buffer_free
    nop
    sh    zero, 0x1E(fp)
    addiu sp, sp, -16
    sw    t1, 0(sp)
    sw    t3, 4(sp)
    sw    t5, 8(sp)
    jal   DRAW_SYNC
    move  a0, zero
    lw    t1, 0(sp)
    lw    t3, 4(sp)
    lw    t5, 8(sp)
    lw    t0, 0x60(fp)
    addiu sp, sp, 16
    nop
@@buffer_free:
    andi  t4, t5, 3             ; t4 = pixels into the first word
    sll   t6, t1, 1
    addu  t6, t6, t1
    sll   t6, t6, 2             ; index * FONT_ROWS
    la    t7, glyph_data + 95
    addu  t1, t7, t6            ; t1 = glyph rows
    lhu   a0, 0xC6(t0)          ; ink
    lhu   a1, 0xC8(t0)          ; background
    lhu   a2, 0xCA(t0)          ; shadow
    addu  t6, t4, t3
    addiu t6, t6, 3
    srl   t6, t6, 2             ; words to upload
    sll   a3, t6, 1             ; a3 = bytes per row
    lhu   t2, 0x1E(fp)          ; the interpreter's own buffer index, zeroed on each of its calls
    nop
    addiu at, t2, 1
    sh    at, 0x1E(fp)
    sll   t2, t2, 9
    addu  t2, t2, t0
    addiu t2, t2, 0xD8          ; t2 = glyph buffer
    addiu t7, t0, W_CARRY
    addu  t8, t5, t3
    srl   t8, t8, 2
    srl   t9, t5, 2
    subu  t8, t8, t9
    sll   t8, t8, 2             ; t8 = bits the pen leaves behind this glyph
    move  v0, zero              ; v0 = previous row's ink, for the shadow
    move  v1, zero              ; v1 = row
@@row:
    beqz  t4, @@no_carry
    move  t9, zero
    lbu   t9, 0(t7)
    nop
    sll   t9, t9, 8
@@no_carry:
    addiu at, v1, -GLYPH_TOP
    sltiu at, at, FONT_ROWS
    beqz  at, @@no_glyph
    nop
    lbu   at, 0(t1)
    addiu t1, t1, 1
    sll   at, at, 8
    srlv  at, at, t4
    or    t9, t9, at            ; t9 = this row's ink, bit 15 = leftmost pixel of the first word
@@no_glyph:
    sllv  at, t9, t8
    srl   at, at, 8
    sb    at, 0(t7)             ; carry for the next glyph
    addiu t7, t7, 1
    sll   t6, t9, 16
    andi  at, v0, 0xFFFF
    or    t6, t6, at            ; t6 = ink in the top half, ink above it in the low half
    move  v0, t9
    move  ra, a3
@@byte:
    bltz  t6, @@left            ; ink > shadow (ink right above) > background, as the original renderer does it
    move  t9, a0
    sll   at, t6, 16
    bltz  at, @@left
    move  t9, a2
    move  t9, a1
@@left:
    sll   at, t6, 1
    bltz  at, @@right
    move  at, a0
    sll   at, t6, 17
    bltz  at, @@right
    move  at, a2
    move  at, a1
@@right:
    sll   at, at, 4
    or    t9, t9, at            ; low nibble = left pixel
    sb    t9, 0(t2)
    addiu t2, t2, 1
    sll   t6, t6, 2
    addiu ra, ra, -1
    bgtz  ra, @@byte
    nop
    addiu v1, v1, 1
    sltiu at, v1, 16
    bnez  at, @@row
    nop
    j     vwf_finish
    nop
dte_table:
.incbin DTE
.endarea

.close
