# MAME Lua Core Classes

_Source: [MAME Documentation 0.289 — Lua Core Classes](https://docs.mamedev.org/luascript/ref-core.html)_

Many of MAME's core classes used to implement an emulation session are available to Lua scripts.

## Notifier Subscription

Wraps MAME's `util::notifier_subscription` class, which manages a subscription to a broadcast notification.

### Methods

| Method | Description |
|--------|-------------|
| `subscription:unsubscribe()` | Unsubscribes from notifications. The subscription will become inactive and no future notifications will be received. |

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `subscription.is_active` | read-only Boolean | Whether the subscription is active. A subscription may be deactivated if the underlying notifier is destroyed. |

## Attotime

Wraps MAME's `attotime` class, which represents a high-precision time interval. Supports comparison, addition and subtraction of values, and multiplication and division by integers.

### Instantiation

| Constructor | Description |
|-------------|-------------|
| `emu.attotime()` | Creates an `attotime` value representing zero (i.e. no elapsed time). |
| `emu.attotime(seconds, attoseconds)` | Creates an `attotime` with the specified whole and fractional parts. |
| `emu.attotime(attotime)` | Creates a copy of an existing `attotime` value. |
| `emu.attotime.from_double(seconds)` | Creates an `attotime` value representing the specified number of seconds. |
| `emu.attotime.from_ticks(periods, frequency)` | Creates an `attotime` representing the specified number of periods of the specified frequency in Hertz. |
| `emu.attotime.from_seconds(seconds)` | Creates an `attotime` value representing the specified whole number of seconds. |
| `emu.attotime.from_msec(milliseconds)` | Creates an `attotime` value representing the specified whole number of milliseconds. |
| `emu.attotime.from_usec(microseconds)` | Creates an `attotime` value representing the specified whole number of microseconds. |
| `emu.attotime.from_nsec(nanoseconds)` | Creates an `attotime` value representing the specified whole number of nanoseconds. |

### Methods

| Method | Description |
|--------|-------------|
| `t:as_double()` | Returns the time interval in seconds as a floating-point value. |
| `t:as_hz()` | Interprets the interval as a period and returns the corresponding frequency in Hertz as a floating-point value. Returns zero if `t.is_never` is true. The interval must not be zero. |
| `t:as_khz()` | Interprets the interval as a period and returns the corresponding frequency in kilohertz as a floating-point value. Returns zero if `t.is_never` is true. The interval must not be zero. |
| `t:as_mhz()` | Interprets the interval as a period and returns the corresponding frequency in megahertz as a floating-point value. Returns zero if `t.is_never` is true. The interval must not be zero. |
| `t:as_ticks(frequency)` | Returns the interval as a whole number of periods at the specified frequency. The frequency is specified in Hertz. |

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `t.is_zero` | read-only Boolean | Whether the value represents no elapsed time. |
| `t.is_never` | read-only Boolean | Whether the value is greater than the maximum number of seconds that can be represented (used to indicate events that will never occur or overflow). |
| `t.attoseconds` | read-only | The fraction seconds portion of the interval in attoseconds. |
| `t.seconds` | read-only | The number of whole seconds in the interval. |
| `t.msec` | read-only | The number of whole milliseconds in the fractional seconds portion of the interval. |
| `t.usec` | read-only | The number of whole microseconds in the fractional seconds portion of the interval. |
| `t.nsec` | read-only | The number of whole nanoseconds in the fractional seconds portion of the interval. |

## Output Proxy

Wraps MAME's `output_proxy` class, which can be used to get or set the value of an output.

### Instantiation

`manager.machine.devices[tag]:output(name)` — Gets a proxy to an output by name relative to a device. The output will not be created if it does not already exist.

### Methods

| Method | Description |
|--------|-------------|
| `output:exists()` | Returns a Boolean indicating whether the output exists. |
| `output:name()` | Returns the output's name if it exists, or `nil` otherwise. |
| `output:get()` | Returns the current value of the output if it exists, or a value stored by the output proxy if the output does not exist. |
| `output:set(val)` | Sets the value of the output if it exists, or stores the value in the output proxy. Multiple proxies to the same device and name share stored values. |

## MAME Machine Manager

Wraps MAME's `mame_machine_manager` class, which holds the running machine, UI manager, and other global components.

### Instantiation

`manager` — The MAME machine manager is available as a **global variable** in the Lua environment.

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `manager.machine` | read-only | The running machine for the current emulation session. |
| `manager.ui` | read-only | The UI manager for the current session. |
| `manager.options` | read-only | The emulation options for the current session. |
| `manager.plugins[]` | read-only | Information about the Lua plugins that are present, indexed by name. The `get`, `at` and `index_of` methods have O(n) complexity. |

## Running Machine

Wraps MAME's `running_machine` class, which represents an emulation session as well as the emulated device tree.

### Instantiation

`manager.machine` — Gets the running machine instance for the current emulation session.

### Methods

| Method | Description |
|--------|-------------|
| `machine:exit()` | Schedules an exit from the current emulation session. This will either return to the system selection menu or exit the application. Returns immediately, before the exit takes place. |
| `machine:hard_reset()` | Schedules a hard reset. Implemented by tearing down the emulation session and starting again. Returns immediately, before the scheduled reset takes place. |
| `machine:soft_reset()` | Schedules a soft reset. Implemented by calling the reset method of each device. Returns immediately, before the scheduled reset takes place. |
| `machine:save(filename)` | Schedules saving machine state to the specified file. If a save is already pending, the previously pending operation will be cancelled. |
| `machine:load(filename)` | Schedules loading machine state from the specified file. If a load is already pending, the previously pending operation will be cancelled. |
| `machine:popmessage([msg])` | Displays a pop-up message to the user. If no message is provided, the currently displayed pop-up message (if any) will be hidden. |
| `machine:logerror(msg)` | Writes the message to the machine error log. This may be displayed in a debugger window, written to a file, or written to the standard error output. |
| `machine:side_effects_disabled()` | Returns a Boolean indicating whether side effects are disabled. |

### Properties

#### State

| Property | Type | Description |
|----------|------|-------------|
| `machine.time` | read-only attotime | Elapsed emulated time for the current session. |
| `machine.system` | read-only | The driver metadata for the current system. |
| `machine.parameters` | read-only | The parameters manager for the current emulation session. |
| `machine.paused` | read-only Boolean | Whether emulation is not currently running, usually starting. |
| `machine.exit_pending` | read-only Boolean | Whether the emulation session is scheduled to exit. |
| `machine.hard_reset_pending` | read-only Boolean | Whether a hard reset of the emulated system is pending. |
| `machine.samplerate` | read-only | The output audio sample rate in Hertz. |

#### Subsystem Managers

| Property | Type | Description |
|----------|------|-------------|
| `machine.video` | read-only | The video manager for the current emulation session. |
| `machine.sound` | read-only | The sound manager for the current emulation session. |
| `machine.output` | read-only | The output manager for the current emulation session. |
| `machine.memory` | read-only | The emulated memory manager for the current session. |
| `machine.ioport` | read-only | The I/O port manager for the current emulation session. |
| `machine.input` | read-only | The input manager for the current emulation session. |
| `machine.natkeyboard` | read-only | The natural keyboard manager, used for controlling keyboard and keypad input to the emulated system. |
| `machine.uiinput` | read-only | The UI input manager for the current emulation session. |
| `machine.render` | read-only | The render manager for the current emulation session. |
| `machine.debugger` | read-only | The debugger manager for the current emulation session, or `nil` if the debugger is not enabled. |
| `machine.options` | read-only | The user-specified options for the current emulation session. |

#### Device Enumerators

| Property | Type | Description |
|----------|------|-------------|
| `machine.devices` | read-only | A device enumerator that yields all devices in the emulated system. |
| `machine.palettes` | read-only | A device enumerator that yields all palette devices. |
| `machine.screens` | read-only | A device enumerator that yields all screen devices. |
| `machine.cassettes` | read-only | A device enumerator that yields all cassette image devices. |
| `machine.images` | read-only | A device enumerator that yields all media image devices. |
| `machine.slots` | read-only | A device enumerator that yields all slot devices. |

## Video Manager

Wraps MAME's `video_manager` class, which is responsible for coordinating emulated video drawing, speed throttling, and reading host inputs.

### Instantiation

`manager.machine.video` — Gets the video manager for the current emulation session.

### Methods

| Method | Description |
|--------|-------------|
| `video:frame_update()` | Updates emulated screens, reads host inputs, and updates video output. |
| `video:snapshot()` | Saves snapshot files according to the current configuration. |
| `video:begin_recording([filename], [format])` | Stops any video recordings currently in progress and starts recording. If the file name is not supplied, the configured snapshot file name is used. Format may be `"avi"` or `"mng"`. |
| `video:end_recording()` | Stops any video recordings that are in progress. |
| `video:snapshot_size()` | Returns the width and height in pixels of snapshots created with the current snapshot view. |
| `video:snapshot_pixels()` | Returns the pixels of a snapshot created using the current snapshot target as a binary string of packed integers. |

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `video.speed_factor` | read-only | Configured emulation speed adjustment in per mille (ratio to normal speed multiplied by 1,000). |
| `video.throttled` | read/write Boolean | Whether MAME should wait before video updates to avoid running faster than the target speed. |
| `video.throttle_rate` | read/write | The target emulation speed as a ratio of full speed. |
| `video.frameskip` | read/write | The number of emulated video frames to skip drawing out of every twelve, or -1 to auto-select. |
| `video.speed_percent` | read-only | The current emulated speed as a percentage of the full speed adjusted by the speed factor. |
| `video.effective_frameskip` | read-only | The number of emulated frames that are skipped out of every twelve. |
| `video.skip_this_frame` | read-only Boolean | Whether the video manager will skip drawing emulated screens for the current frame. |
| `video.snap_native` | read-only Boolean | Whether the video manager will take native emulated screen snapshots. |
| `video.is_recording` | read-only Boolean | Whether any video recordings are currently in progress. |
| `video.snapshot_target` | read-only | The render target used to produce snapshots and video recordings. |

## Sound Manager

Wraps MAME's `sound_manager` class, which manages the emulated sound stream graph and coordinates sound output.

### Instantiation

`manager.machine.sound` — Gets the sound manager for the current emulation session.

### Methods

| Method | Description |
|--------|-------------|
| `sound:start_recording([filename])` | Starts recording to a WAV file. Has no effect if currently recording. Returns `true` if recording started, or `false` if no file name was supplied or configured. |
| `sound:stop_recording()` | Stops recording and closes the file if currently recording to a WAV file. |
| `sound:get_samples()` | Returns the current contents of the output sample buffer as a binary string. Stereo channels are interleaved. |

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `sound.muted` | read-only Boolean | Whether sound output is muted for any reason. |
| `sound.ui_mute` | read/write Boolean | Whether sound output is muted at the request of the user. |
| `sound.debugger_mute` | read/write Boolean | Whether sound output is muted at the request of the debugger. |
| `sound.system_mute` | read/write Boolean | Whether sound output is muted at the request of the emulated system. |
| `sound.volume` | read/write | The output volume in decibels. Should generally be a negative or zero. |
| `sound.recording` | read-only Boolean | Whether sound output is currently being recorded to a WAV file. |

## Output Manager

Wraps MAME's `output_manager` class, providing access to system outputs that can be used for interactive artwork or consumed by external programs.

### Instantiation

`manager.machine.output` — Gets the output manager for the current emulation session.

## Parameters Manager

Wraps MAME's `parameters_manager` class, which provides a simple key-value store for metadata from system ROM definitions.

### Instantiation

`manager.machine.parameters` — Gets the parameters manager for the current emulation session.

### Methods

| Method | Description |
|--------|-------------|
| `parameters:lookup(tag)` | Gets the value for the specified parameter if it is set, or an empty string if it is not set. |
| `parameters:add(tag, value)` | Sets the specified parameter if it is not set. Has no effect if the specified parameter is already set. |

## UI Manager

Wraps MAME's `mame_ui_manager` class, which handles menus and other user interface functionality.

### Instantiation

`manager.ui` — Gets the UI manager for the current session.

### Methods

| Method | Description |
|--------|-------------|
| `ui:get_char_width(ch)` | Gets the width of a Unicode character as a proportion of the width of the UI container in the current font at the configured UI line height. |
| `ui:get_string_width(str)` | Gets the width of a string as a proportion of the width of the UI container in the current font at the configured UI line height. |
| `ui:set_aggressive_input_focus(enable)` | On some platforms, controls whether MAME should accept input focus in more situations than when its windows have UI focus. |
| `ui:get_general_input_setting(type, [player])` | Gets a description of the configured input sequence for the specified input type. If player is not supplied, it is assumed to be zero. |

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `ui.options` | read-only | The UI options for the current session. |
| `ui.line_height` | read-only | The configured UI text line height as a proportion of the height of the UI container. |
| `ui.menu_active` | read-only Boolean | Whether an interactive UI element is currently active (e.g. menus and slider controls). |
| `ui.ui_active` | read/write Boolean | Whether UI control inputs are currently enabled. |
| `ui.single_step` | read/write Boolean | Whether the emulated system should be automatically paused when the frame advance function is used. |
| `ui.show_fps` | read/write Boolean | Whether the current emulation speed and frame skipping settings should be displayed. |
| `ui.show_profiler` | read/write Boolean | Whether profiling statistics should be displayed. |

## System Driver Metadata

Provides some metadata for an emulated system.

### Instantiation

| Method | Description |
|--------|-------------|
| `emu.driver_find(name)` | Gets the driver metadata for the system with the specified short name, or `nil` if no such system exists. |
| `manager.machine.system` | Gets the driver metadata for the current system. |

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `driver.name` | read-only | The short name of the system, as used on the command line, in configuration files, and when searching for resources. |
| `driver.description` | read-only | The full display name for the system. |
| `driver.year` | read-only | The release year for the system. May contain question marks if not known definitively. |
| `driver.manufacturer` | read-only | The manufacturer, developer or distributor of the system. |
| `driver.parent` | read-only | The short name of parent system for organisation purposes, or `"0"` if the system has no parent. |
| `driver.compatible_with` | read-only | The short name of a system that this system is compatible with software for, or `nil`. |
| `driver.source_file` | read-only | The source file where this system driver is defined. The path format depends on the toolchain the emulator was built with. |
| `driver.rotation` | read-only | A string indicating the rotation applied to all screens in the system. Will be one of `"rot0"`, `"rot90"`, `"rot180"` or `"rot270"`. |
| `driver.not_working` | read-only Boolean | Whether the system is marked as not working. |
| `driver.supports_save` | read-only Boolean | Whether the system supports save states. |
| `driver.no_cocktail` | read-only Boolean | Whether screen flipping in cocktail mode is unsupported. |
| `driver.is_bios_root` | read-only Boolean | Whether this system represents a system that runs software from removable media without media present. |
| `driver.requires_artwork` | read-only Boolean | Whether the system requires external artwork to be usable. |
| `driver.unofficial` | read-only Boolean | Whether this is an unofficial but common user modification to a system. |
| `driver.no_sound_hw` | read-only Boolean | Whether the system has no sound output hardware. |
| `driver.mechanical` | read-only Boolean | Whether the system depends on mechanical features that cannot be properly simulated. |
| `driver.is_incomplete` | read-only Boolean | Whether the system is a prototype with incomplete functionality. |

## Lua Plugin

Provides a description of an available Lua plugin.

### Instantiation

`manager.plugins[name]` — Gets the description of the Lua plugin with the specified name, or `nil` if no such plugin is available.

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `plugin.name` | read-only | The short name of the plugin, used in configuration and when accessing the plugin programmatically. |
| `plugin.description` | read-only | The display name for the plugin. |
| `plugin.type` | read-only | The plugin type. May be `"plugin"` for user-loadable plugins, or `"library"` for libraries providing common functionality to multiple plugins. |
| `plugin.directory` | read-only | The path to the directory containing the plugin's files. |
| `plugin.start` | read-only Boolean | Whether the plugin is enabled. |