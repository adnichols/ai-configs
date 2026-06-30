---
name: gaming-and-emulation
description: "Host modded Minecraft servers and play classic games via headless emulation with RAM state reading."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [minecraft, emulation, gaming, pokemon, modpack]
    related_skills: []
---

# Gaming and Emulation

## Minecraft Modpack Servers

Host modded Minecraft servers using CurseForge or Modrinth modpacks.

### Setup (Docker Recommended)
```bash
docker run -d \
  -v /data/minecraft:/data \
  -e TYPE=CURSEFORGE \
  -e CF_SERVER_MOD=/data/modpack.zip \
  -p 25565:25565 \
  --name mc-server \
  itzg/minecraft-server
```

### Modrinth
```bash
docker run -d \
  -v /data/minecraft:/data \
  -e TYPE=MODRINTH \
  -e MODRINTH_PROJECT=modpack-slug \
  -p 25565:25565 \
  itzg/minecraft-server
```

### Management
```bash
docker exec mc-server mc-server console        # Attach to console
docker exec mc-server mc-server backup         # Trigger backup
docker exec mc-server mc-server stop           # Graceful stop
```

### Server Properties
Edit `/data/server.properties` for:
- `difficulty=hard`
- `max-players=20`
- `white-list=true`

### Backups
Mount a backup volume and use `mc-server backup` or configure cron inside the container.

## Pokemon Player (Headless Emulation)

Play Pokemon (and other Game Boy / GBA games) via a headless emulator with RAM state reading.

### Setup
```bash
# Install emulator + Python bindings
pip install pyboy
```

### Basic Script
```python
from pyboy import PyBoy

pyboy = PyBoy("pokemon-red.gb")
pyboy.set_emulation_speed(0)  # Unlimited speed for training

while pyboy.tick():
    # Read RAM state
    player_x = pyboy.memory[0xD362]
    player_y = pyboy.memory[0xD361]
    
    # Decide action based on state
    if player_x < target_x:
        pyboy.button_press("right")
    else:
        pyboy.button_release("right")
```

### RAM Map
Common Pokemon Red/Blue addresses:
- `0xD163` — Party count
- `0xD16B` — First Pokemon species
- `0xD18C` — First Pokemon HP
- `0xD35D` — Current map ID

### Use Cases
- Automated grinding / training
- Speedrun routing via state analysis
- AI agent training (reinforcement learning)

### Pitfalls
- Save states are emulator-specific; don't mix across versions
- RAM addresses differ between Pokemon versions (Red vs Blue vs Yellow)
- PyBoy requires a display for some features; use `headless=True` on servers
