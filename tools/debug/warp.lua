-- warp.lua: cold boot to any scene in tools/debug/scenes.tsv, by RAM poke only (no ROM change, no save needed).
-- Use: emu.py game.cue --out DIR --script tools/debug/warp.lua --var "SCENE='ch1_card'" --var "ROOT='H:/.../repo/'" --frames N
-- Optional global: GOD=1 (pin player HP in battle). How every value was found: docs/re/warp.md.
--
-- How it works: SYO00 idles at 0x800C4768 until 0x8009AE34 is non-zero, which the title's START writes. The script
-- presses circle on the title; SYO00 then writes chapter=1/scene=0 and waits two vsyncs (0x800C478C) before reading
-- the chapter, so pokes on every frame win. The chapter's main later reads the scene word and jumps through its table;
-- a `jump` scene overwrites that table slot while the overlay loads. chapter=0 stays on the title for the route.
local mem = PCSX.getMemPtr()
local function r8(a) return mem[a & 0x1FFFFF] end
local function r16(a) a = a & 0x1FFFFF; return mem[a] + mem[a + 1] * 0x100 end
local function r32(a) a = a & 0x1FFFFF; return mem[a] + mem[a + 1] * 0x100 + mem[a + 2] * 0x10000 + mem[a + 3] * 0x1000000 end
local function w16(a, v) a = a & 0x1FFFFF; v = v % 0x10000; mem[a] = v % 256; mem[a + 1] = math.floor(v / 256) end
local function w32(a, v)
  a = a & 0x1FFFFF
  v = v % 0x100000000
  for i = 0, 3 do mem[a + i] = v % 256; v = math.floor(v / 256) end
end
local function s16(v) return v >= 0x8000 and v - 0x10000 or v end

local CHAPTER, SCENE_W, TITLE_RESULT = 0x8009AE68, 0x8009AE28, 0x8009AE34
local TITLE_ENTRY_VA, TITLE_ENTRY_WORD = 0x801D82C8, 0x27BDFFC8  -- first instruction of TITLE.BIN's start routine
local SYO00_IDLE_VA, SYO00_IDLE_WORD = 0x800C4768, 0x0C00DD2F    -- jal vsync in SYO00's title loop
local BATTLE_ENTRY_VA, BATTLE_ENTRY_WORD = 0x801D9478, 0x27BDFFE8 -- BATTLE.BIN start routine
local BATTLE_PTR = 0x801F7B20                                    -- battle state; +0x138 player HP, +0x288 enemy HP
local HP_PLAYER, HP_PLAYER_MAX, HP_ENEMY = 0x138, 0x13A, 0x288
local WINDOWS_PTR, WINDOW_SIZE = 0x8009ACF0, 0x7DC               -- gp+0x16C (gp = 0x8009AB84); window = *ptr + i * size

-- Each chapter's scene jump table: address and its first word (to know the overlay arrived). Index = scene + 10.
local TABLES = {
  { at = 0x800C440C, want = 0x800DBD20 },
  { at = 0x800C321C, want = 0x800D3FC4 },
  { at = 0x800C2D9C, want = 0x800D9054 },
  { at = 0x800C2D8C, want = 0x800DD83C },
  { at = 0x800C29EC, want = 0x800D0A74 },
  { at = 0x800C2C0C, want = 0x800D2940 },
  { at = 0x800C2EE4, want = 0x800D6698 },
}

local sc
do
  local f = assert(io.open((ROOT or "") .. "tools/debug/scenes.tsv", "r"))
  local head = {}
  for line in f:lines() do
    local c = {}
    for v in (line .. "\t"):gmatch("([^\t]*)\t") do c[#c + 1] = v end
    if #head == 0 then
      head = c
    elseif c[1] == SCENE then
      sc = {}
      for i, k in ipairs(head) do sc[k] = c[i] ~= "-" and c[i] or nil end
    end
  end
  f:close()
end
if not sc then error("unknown SCENE: " .. tostring(SCENE)) end
local chapter, scene = tonumber(sc.chapter), tonumber(sc.scene)
local jump, say = tonumber(sc.jump), SAY or tonumber(sc.say)  -- SAY: the string's address on this build (warp_all.py)
local tab = chapter > 0 and TABLES[chapter] or nil
local flags = sc.flags or ""
local god = (GOD or 0) ~= 0 or flags:find("god")
local lose, win = flags:find("lose"), flags:find("win")
if sc.pokes then
  sc.poke_list = {}
  for a, v in sc.pokes:gmatch("(0x%x+)=(%-?%w+)") do sc.poke_list[#sc.poke_list + 1] = { tonumber(a), tonumber(v) } end
end

local function press_route(spec)
  for step in spec:gmatch("[^;]+") do
    local f, b = step:match("%s*(%d+)%s+(%S+)")
    L.press(b, tonumber(f))
  end
end

local function battle_state()
  if r32(BATTLE_ENTRY_VA) ~= BATTLE_ENTRY_WORD then return nil end
  local p = r32(BATTLE_PTR)
  if p < 0x80000000 or p >= 0x80200000 then return nil end
  return p
end

local title_seen, state, done_at, said, poked = 0, "wait_title", nil, false, false
L.on_frame(function(n)
  if n % 300 == 0 then
    local p = battle_state()
    local hp = p and string.format(" hp=%d/%d enemy=%d", s16(r16(p + HP_PLAYER)), s16(r16(p + HP_PLAYER_MAX)), s16(r16(p + HP_ENEMY))) or ""
    L.log(string.format("%d chapter=%d scene=%d%s", n, r32(CHAPTER), s16(r32(SCENE_W) % 0x10000), hp))
  end
  local p = done_at and battle_state()
  if p then
    -- Stage 56 and others inherit HP from the battle before them, so a warp starts at 0: pin regardless of current HP.
    if god and not lose and r16(p + HP_PLAYER_MAX) > 0 then w16(p + HP_PLAYER, r16(p + HP_PLAYER_MAX)) end
    if not poked and n > done_at + 900 and s16(r16(p + HP_PLAYER)) > 0 then
      if lose then w16(p + HP_PLAYER, 0); L.log(n .. " poke lose"); poked = true end
      if win then w16(p + HP_ENEMY, 0); L.log(n .. " poke win"); poked = true end
    end
  end
  if say and done_at and not said and n > done_at + (tonumber(sc.say_wait) or 600) then
    local base = r32(WINDOWS_PTR)  -- zero until the first text of the run has created the windows
    if base >= 0x80000000 and base < 0x80200000 then
      local win_i = tonumber(sc.say_win) or 0
      local w = base + win_i * WINDOW_SIZE
      local k = r16(w + 0x5E)
      w32(w + 0x68 + 4 * k, say)
      w16(w + 0x5E, k + 1)
      w16(w + 0x518, 0)
      if r16(w + 0x58) == 0 then w16(w + 0x58, 1) end
      L.log(string.format("%d say %08X window %d", n, say, win_i))
      said = true
    end
  end
  if state == "wait_title" then
    local at_title = r32(TITLE_ENTRY_VA) == TITLE_ENTRY_WORD and r32(SYO00_IDLE_VA) == SYO00_IDLE_WORD
    title_seen = at_title and title_seen + 1 or 0
    if not at_title and n % 120 == 0 and L.route_done() then L.press("start", 6) end  -- skip the logo and opening FMVs
    if title_seen >= 90 then
      L.log(string.format("%d title idle", n))
      if chapter == 0 then
        state, done_at = "done", n
        if sc.route then press_route(sc.route) end
      else
        -- A real press, not a poke of the result word: the title's handler also kills its own task (0x82). A task
        -- left alive keeps running from TITLE.BIN's memory after BATTLE.BIN loads over it, and the emulator hangs.
        L.press("circle", 6)
        state = "started"
      end
    end
  elseif state == "started" then
    if r32(TITLE_RESULT) ~= 0 then
      L.log(string.format("%d title result %d", n, r32(TITLE_RESULT)))
      state = "poke"
    elseif n % 30 == 0 and L.route_done() then
      L.press("circle", 6)  -- the title ignores input during its fade-in, with no flag worth reading: press until it takes
    end
  elseif state == "poke" then
    w32(CHAPTER, chapter)
    w32(SCENE_W, scene)
    if r32(tab.at) == tab.want then  -- table sits in the file's first sectors; main runs only after the last one
      if sc.poke_list then for _, pv in ipairs(sc.poke_list) do w32(pv[1], pv[2]) end end
      L.log(string.format("%d overlay present", n))
      state, done_at = "done", n
      if sc.route then press_route(sc.route) end
    end
  end
  -- Keep rewriting the slot while the overlay loads: a table can straddle a sector, so its first word arrives before
  -- the slot and the later sector would overwrite a single write (chapter 6, table at file 0xFE4). 600 frames outlasts
  -- the largest load (chapter 7, 266 sectors); the first-word test stops it if another overlay has replaced this one.
  if jump and done_at and n <= done_at + 600 and r32(tab.at) == tab.want then
    w32(tab.at + 4 * (scene + 10), jump)
  end
end)
