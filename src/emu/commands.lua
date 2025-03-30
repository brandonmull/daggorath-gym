local function enter()
    input.set_value("P1_START", 1)  -- Simulate pressing the Enter key
    emu.wait(0.1)  -- Wait for 100 milliseconds
    input.set_value("P1_START", 0)  -- Release the Enter key
end

return { enter }