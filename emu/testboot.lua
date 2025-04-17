local socket = require("socket")

local client = socket.connect("127.0.0.1", 8080)

client:send("Hello, server!")

client:close()


