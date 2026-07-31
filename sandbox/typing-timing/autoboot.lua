local emu_dir = os.getenv("AUTOBOOT_DIR")
if emu_dir then
    package.path = emu_dir .. "/?.lua;" .. package.path
end

local frame = 0
local nk = manager.machine.natkeyboard
emu.add_machine_frame_notifier(function()
    frame = frame + 1
    if frame == 1 then
        nk:post("\r")
        nk:post("\r")
        nk:post("PULL LEFT TORCH\r")
        nk:post("USE LEFT TORCH\r")
    end
end)