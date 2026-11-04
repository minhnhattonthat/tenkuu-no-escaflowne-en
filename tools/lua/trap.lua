-- trap.lua: log every read or write of the ranges in TRAP (needs --debugger): are these bytes really free?
-- Use: emu.py ... --debugger --script tools/lua/trap.lua --var "TRAP={{0x80083750,0x80083952},...}"
-- One line per range and access kind per program counter, so a tight loop costs one line.
local ffi = require("ffi")
local seen = {}
for _, r in ipairs(TRAP) do
  local lo, hi = r[1], r[2]
  local function hook(kind)
    return function(addr)
      local pc = tonumber(ffi.cast("uint32_t", L.pc()))
      local key = kind .. lo .. pc
      if not seen[key] then
        seen[key] = true
        L.log(string.format("trap %s %08X-%08X at %08X pc=%08X", kind, lo, hi, tonumber(addr) or 0, pc))
      end
    end
  end
  L.on_read(lo, hi - 1, hook("read"))
  L.on_write(lo, hi - 1, hook("write"))
end
