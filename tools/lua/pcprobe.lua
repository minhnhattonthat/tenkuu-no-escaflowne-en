-- pcprobe.lua: every PC_EVERY frames (default 60), log pc, ra, sp and the game's scene words. Finds where a run sits.
local ffi = require("ffi")
local mem = PCSX.getMemPtr()
local function r32(a) a = a & 0x1FFFFF; return mem[a] + mem[a + 1] * 0x100 + mem[a + 2] * 0x10000 + mem[a + 3] * 0x1000000 end
L.on_frame(function(n)
  if n % (PC_EVERY or 60) == 0 then
    local R = PCSX.getRegisters()
    L.log(string.format("%d pc=%08X ra=%08X sp=%08X chap=%d scene=%08X ae34=%08X", n, tonumber(ffi.cast("uint32_t", R.pc)),
      tonumber(ffi.cast("uint32_t", R.GPR.n.ra)), tonumber(ffi.cast("uint32_t", R.GPR.n.sp)), r32(0x8009AE68), r32(0x8009AE28), r32(0x8009AE34)))
  end
end)
