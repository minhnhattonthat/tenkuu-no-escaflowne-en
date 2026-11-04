-- winlog.lua: every WIN_EVERY frames (default 120), log the text windows' fields while they exist. Use with warp.lua.
local mem = PCSX.getMemPtr()
local function r8(a) return mem[bit.band(a, 0x1FFFFF)] end
local function r16(a) a = bit.band(a, 0x1FFFFF); local v = mem[a] + mem[a + 1] * 256; if v >= 32768 then v = v - 65536 end; return v end
local function r32(a) a = bit.band(a, 0x1FFFFF); return mem[a] + mem[a + 1] * 256 + mem[a + 2] * 65536 + mem[a + 3] * 16777216 end
local every = WIN_EVERY or 120
L.on_frame(function(n)
  if n % every ~= 0 then return end
  local base = r32(0x8009ACF0)
  if base == 0 then return end
  for i = 0, 2 do
    local w = base + 0x24 + i * 0x7DC
    local state = r16(w + 0x34)
    if state ~= 0 then
      local s = string.format("%d win%d %08X st=%d xy=%d,%d wh=%d,%d vram=%d,%d size=%d,%d pen=%d,%d cc=%d ce=%d c4=%04X ink=%d bg=%d sh=%d d6=%d ptr=%08X",
        n, i, w, state, r16(w), r16(w + 2), r16(w + 4), r16(w + 6), r16(w + 0x2C), r16(w + 0x2E), r16(w + 0x30), r16(w + 0x32),
        r16(w + 0x36), r16(w + 0x38), r16(w + 0xCC), r16(w + 0xCE), r16(w + 0xC4), r16(w + 0xC6), r16(w + 0xC8), r16(w + 0xCA), r16(w + 0xD6), r32(w + 0x40))
      local tail = 0
      for o = 0x358, 0x4D7 do if r8(w + o) ~= 0 then tail = tail + 1 end end
      L.log(s .. " tail_nonzero=" .. tail)
    end
  end
end)
