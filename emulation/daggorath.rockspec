package = "daggorath-gym"
version = "scm-1"  -- Special version for development/source control

source = {
   url = "git://github.com/username/daggorath-gym",  -- Replace with your repo URL if applicable
}

description = {
   summary = "Daggorath Gym for Reinforcement Learning",
   detailed = [[
      A Gymnasium-compatible environment for Dungeons of Daggorath
      using MAME emulation.
   ]],
   homepage = "https://github.com/username/daggorath-gym",  -- Replace with your repo
   license = "MIT"  -- Adjust license as needed
}

dependencies = {
   "lua >= 5.3",
   "luasocket >= 3.0",
   "luafilesystem >= 1.8.0"
}

build = {
   type = "builtin",
   modules = {}
} 