## 🕹️ Pixel Vengeance AI

**Pixel Vengeance AI** is a 2D retro-style arcade shooter built in Python using Pygame. The game features dynamic enemy waves and an AI-powered final boss that adapts its attack patterns based on its state. Choose your jet, dodge swarms of bullets, and face off against a boss powered by a local Ollama AI model.

---

### 🎮 Features

* Multiple player jet types with different stats and abilities.
* Dynamic wave-based enemy spawning.
* AI-powered boss behavior with adaptive attack patterns.
* Rich audio-visual effects and power-ups.
* Super Laser and Bomb mechanics for high-impact plays.
* Optional Ollama integration for true AI-driven decision-making.

---

### 🚀 Getting Started

#### Prerequisites

* Python 3.8+
* [Pygame](https://www.pygame.org/)
* [Ollama](https://ollama.com/) (optional, for AI boss)
* A downloaded Ollama model like `phi3:mini`

#### Run the Game

```bash
python main.py
```

If Ollama is not running or the model isn't available, the game will fall back to a scripted boss AI.

---

### 🧠 Boss AI: Behavior & Attacks

#### AI Architecture (With Ollama)

1. **State Monitoring:** The boss tracks its own health, time since last action, and shield state.
2. **AI Invocation:** Every 10 seconds (if not thinking), the boss asks the local Ollama AI to choose a sequence of actions.
3. **System Prompt:** The boss sends a strict prompt instructing Ollama to reply with a comma-separated list of 3–4 attack/movement actions.
4. **Fallback Logic:** If AI fails, the boss uses a pre-defined fallback sequence.

#### Random Walk Algorithm (Boss Movement)

The boss uses a **randomized horizontal movement** system:

* Every 2 seconds, it chooses a new direction: `MOVE_LEFT` or `MOVE_RIGHT`.
* While moving, it checks screen boundaries and bounces back if it hits them.
* When dodging (via the `DODGE` action), it teleports \~90px to either side.

This creates the feeling of a pseudo-random walk, making its motion unpredictable.

---

### ☠️ Boss Attack Types

| Attack Name      | Description                                                                 |
| ---------------- | --------------------------------------------------------------------------- |
| `SINGLE_SHOT`    | Fires one bullet straight down.                                             |
| `SPREAD_SHOT`    | Fires three bullets in a fan-like arc.                                      |
| `VOLLEY_SHOT`    | Fires three bullets sequentially downward.                                  |
| `CIRCLE_SHOT`    | Fires bullets in 360°, like a radial explosion.                             |
| `LASER_SWEEP`    | Charges a giant laser and fires it vertically—high damage.                  |
| `HOMING_MISSILE` | A missile that homes in on the player's position.                           |
| `LAY_MINES`      | Deploys area-denial mines on the playfield.                                 |
| `SUMMON_MINIONS` | Periodically spawns regular enemies to assist.                              |
| `DODGE`          | Sidesteps quickly (\~90px) to avoid damage.                                 |
| `SHIELD`         | Activates at certain HP thresholds, absorbing all damage for a few seconds. |

---

### 🎯 Jet Types

| Jet         | Speed | Lives | Bombs | Special              |
| ----------- | ----- | ----- | ----- | -------------------- |
| Interceptor | 8     | 1     | 3     | Balanced stats       |
| Striker     | 7     | 1     | 1     | Fires double bullets |
| Tank        | 6     | 3     | 2     | Extra health         |
| Wraith      | 11    | 1     | 2     | High speed           |

---

### 🧱 Game Architecture Diagram

Below is the conceptual architecture. You can [import this into draw.io](https://draw.io) or use the XML directly.

```
+----------------------+
|      main.py         |
+----------+-----------+
           |
           v
+----------+-----------+
| Game Initialization |
+----------+-----------+
           |
           v
+----------+-----------+       +------------------------+
|  Pygame Loop         |<----->| Input Event Handling   |
|  (update/draw/tick)  |       +------------------------+
+----------+-----------+
           |
           v
+------------------------------+
| Entity Managers (Groups):    |
| - all_sprites                |
| - enemies, bullets, etc.     |
+------------------------------+
           |
           v
+------------------------------+
| Player                       |
| - Movement                  |
| - Shooting / Bombs         |
| - Powerups & Lives         |
+------------------------------+
           |
           v
+------------------------------+
| Boss (AI or Scripted)        |
| - Attacks & Behavior        |
| - Health / Shield System    |
+------------------------------+
           |
           v
+------------------------------+
| Ollama Client (Optional)     |
| - Prompts / Chat Interface  |
| - Action Sequence Handling  |
+------------------------------+
