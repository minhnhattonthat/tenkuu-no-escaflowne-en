Tenkuu no Escaflowne (The Vision of Escaflowne), PlayStation: English patch v{version}

Unofficial fan translation. It contains no game data: you need your own dump of the Japanese disc.

WHAT YOU NEED
  Tenkuu no Escaflowne (Japan), serial SLPS-01015, the standard edition, as a .cue with two .bin tracks:

  Track 1  (the patch applies to this file only)
    size   {t1_size} bytes
    CRC32  {t1_crc32}
    MD5    {t1_md5}
    SHA-1  {t1_sha1}
  Track 2  (leave it unpatched)
    size   {t2_size} bytes
    CRC32  {t2_crc32}
    MD5    {t2_md5}
    SHA-1  {t2_sha1}

HOW TO PATCH
  1. Check Track 1 against the hashes above. A different dump will not patch correctly.
  2. Apply {patch} to Track 1 with Delta Patcher, or from a command line:
       xdelta3 -d -s "Tenkuu no Escaflowne (Japan) (Track 1).bin" {patch} "patched.bin"
  3. Keep your Track 2 and your .cue. Either replace Track 1 with the patched file under the same name, or point the
     first FILE line of the .cue at patched.bin.
  4. Boot the .cue. Patched Track 1: CRC32 {patched_crc32}, SHA-1 {patched_sha1}.

Confirm is circle and cancel is cross, as on the Japanese game.
Tested in PCSX-Redux with a Japanese BIOS. Start from a cold boot, not from an emulator savestate of the Japanese game:
a savestate holds the old text and code. Memory card saves are separate: see the limits below.

WHAT IS TRANSLATED
  Dialogue and story        English
  Menus and system text     English
  Title, chapter cards      English
  Staff roll                English
  Opening video's logo      English
  Other videos              Japanese speech, no subtitles (57 videos, about 21 minutes)
  Voiced lines              Japanese audio under English text

KNOWN LIMITS
  - Long lines run on to extra text pages. Voice clips are timed to the Japanese pages, so speech and pages may not
    always line up. Nobody has checked this by ear.
  - The glare over the logo in the opening video is missing.
  - The shrine box in chapter 1's map art keeps its Japanese character: it is scenery.
  - Names the game invented, with no official spelling to follow, are best guesses: Jechia, Getin, Helio, Zodia, Gimle,
    Theo, Dilate, Rampant, Godashim, Zegu, Kaja, Refine.
  - Memory card saves made with the patched game were tested. Saves from the unpatched game were not.

Report bugs: https://github.com/minhnhattonthat/tenkuu-no-escaflowne-en/issues
A save file or savestate with your report helps most.

Tools and translation: MIT. The game is (c) its owners; this project is not affiliated with them.
Do not share patched images. Made with extensive AI assistance (Claude by Anthropic). Corrections are very welcome.
