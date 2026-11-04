-- drawlog.lua: log every glyph the text engine draws: frame, SJIS code, window struct, upload RECT (needs --debugger).
-- 0x80039AD4 = glyph renderer (a0 = SJIS code); 0x8003ADC0 = LoadImage call just after it (a0 = RECT*, a1 = pixels).
local ffi = require("ffi")
local mem = PCSX.getMemPtr()
local function r16(a) a = bit.band(a, 0x1FFFFF); return mem[a] + mem[a + 1] * 256 end
local function reg(n) return PCSX.getRegisters().GPR.n[n] end

L.on_exec(0x80039AD4, function()
  local c = tonumber(ffi.cast("uint32_t", reg("a0")))
  L.log(string.format("%d glyph %04X", L.frame, c))
end)
L.on_exec(0x8003ADC0, function()
  local p = tonumber(ffi.cast("uint32_t", reg("a0")))
  local s = tonumber(ffi.cast("uint32_t", reg("a1")))
  L.log(string.format("%d rect %d,%d %dx%d src %08X", L.frame, r16(p), r16(p + 2), r16(p + 4), r16(p + 6), s))
end)
