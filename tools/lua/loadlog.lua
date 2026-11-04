-- loadlog.lua: log each LoadImage call's rect, once per distinct (ra, y, h, w). Needs --debugger.
local mem = PCSX.getMemPtr()
local function r16(a) a = bit.band(a, 0x1FFFFF); return mem[a] + mem[a + 1] * 256 end
local seen, n = {}, 0
L.on_exec(0x80063A7C, function()
  local R = PCSX.getRegisters().GPR.n
  local a0, ra = tonumber(ffi.cast("uint32_t", R.a0)), tonumber(ffi.cast("uint32_t", R.ra))
  local x, y, w, h = r16(a0), r16(a0 + 2), r16(a0 + 4), r16(a0 + 6)
  local k = string.format("ra=%08X y=%d w=%d h=%d", ra, y, w, h)
  n = n + 1
  if not seen[k] then
    seen[k] = true
    L.log(string.format("%d load#%d x=%d %s", L.frame, n, x, k))
  end
end)
