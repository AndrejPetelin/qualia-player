# 🎵 Qualia Player

**AI-powered playlist generator using local LLM and your music library**

Qualia Player uses Mistral (via Ollama) to intelligently create playlists from your local music collection. Instead of relying on unreliable metadata tags, it leverages the LLM's actual music knowledge to understand genres, artists, and vibes.

Built by [Andrej](https://github.com/YOUR_GITHUB) & Irene from [Alienish Games](https://alienishgames.com)

---

## ✨ Features

- 🤖 **Smart Genre Matching** - Uses Mistral's music knowledge instead of metadata tags
- 🎲 **Random Track Selection** - Different songs each time you generate a playlist
- 💬 **Natural Language Requests** - "Make me a 3-hour prog metal playlist with some Whitesnake"
- 📁 **Local Library** - Works entirely with your music files
- 👀 **Folder Monitoring** - Auto-detects when you add new music
- 🎯 **Flexible Queries** - Genre, artist, decade, mood, vocals, instrumentals
- 📝 **M3U Export** - Universal playlist format works with any player

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- [Ollama](https://ollama.ai) installed and running
- A local music library (MP3, FLAC, OGG, M4A, WAV, OPUS)

### Installation
```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/qualia-player.git
cd qualia-player

# Install dependencies
pip install -r requirements.txt

# Make sure Ollama is running with Mistral
ollama pull mistral
ollama serve

# Run the app
python main.py
```

### First Run

1. Click **"Change Folder"** and select your music directory
2. Wait for the library scan to complete
3. Start making playlists!

---

## 📖 Usage Examples

### Genre-Based Playlists
```
"Make me a prog metal playlist, 3 hours"
"Hard rock from the 80s, about 45 minutes"
"Instrumental music for focus"
```

### Artist-Specific
```
"Progressive rock with some Pink Floyd mixed in"
"Whitesnake and similar bands, 1 hour"
```

### Attribute-Based
```
"Songs with female vocalists"
"Tracks where Mike Portnoy plays drums"
"Music in languages other than English"
```

---

## 🛠️ How It Works

### Two-Phase LLM Approach

**Phase 1: Genre Filtering**
- Sends your artist catalog (with sample track names) to Mistral
- Mistral uses its music knowledge to filter artists matching your request
- Example: "prog metal" → Dream Theater ✅, Queensrÿche ✅, Avenged Sevenfold ❌

**Phase 2: Smart Selection**
- Mistral decides how many tracks from each artist for variety
- Python randomly selects tracks from each artist
- Generates M3U playlist file

### Why This Works Better Than Metadata

Traditional playlist generators rely on genre tags like:
- `"Rock"` (too broad - includes everything!)
- `"Progressive Metal, Hard Rock, Metal"` (comma-separated mess)
- `"Heavy y Metal"` (typos in tags)

Qualia Player uses Mistral's training on millions of music discussions to understand:
- Which artists actually belong to which genres
- Related/similar artists and styles
- Nuanced requests like "deep cuts" or "female-fronted bands"

---

## 📁 Project Structure
```
qualia-player/
├── main.py                 # Application entry point
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── database/
│   ├── db_manager.py      # SQLite operations
│   └── models.py          # Track data model
├── scanner/
│   ├── music_scanner.py   # Metadata extraction (mutagen)
│   └── folder_monitor.py  # Filesystem watching (watchdog)
├── llm/
│   └── ollama_client.py   # Mistral integration
├── playlist/
│   └── generator.py       # M3U file creation
└── ui/
    └── chat_window.py     # Tkinter interface
```

---

## ⚙️ Configuration

Edit `config.py` to customize:
```python
# Music folder location
MUSIC_FOLDER = Path.home() / "Music"

# Ollama settings
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "mistral"  # or "llama3", "qwen", etc.

# Playlist output location
PLAYLIST_OUTPUT = Path.home() / "Music" / "Playlists"

# Supported audio formats
AUDIO_EXTENSIONS = {'.mp3', '.flac', '.ogg', '.m4a', '.wav', '.opus'}
```

---

## 🐛 Known Issues & Future Ideas

### Current Limitations
- [ ] Playlist names aren't unique (gets overwritten)
- [ ] Decade filtering not implemented yet (asks for "80s" but plays all decades)
- [ ] "Live music" detection needs work
- [ ] First N tracks are always in album order

### Future Features (We're brainstorming!)
- [ ] **DJ Personalities** - Different voices/styles ("Cynical DJ", "NPR Host", "Pirate Radio")
- [ ] **GTA-style Radio** - AI-generated DJ banter, fake ads ("Lazernation - discount blasters!")
- [ ] **Deep Cuts Mode** - Avoid singles/popular tracks
- [ ] **Singles Mode** - Only the hits
- [ ] **Duration Filtering** - "Songs over 8 minutes" for prog epics
- [ ] **Decade/Year Filtering** - Proper 80s, 90s, etc. detection
- [ ] **Tidal Integration** - Generate playlists in Tidal account
- [ ] **Spotify Integration** - Same but for Spotify

---

## 🤝 Contributing

We built this in one intense evening with Claude (Anthropic's AI). It works surprisingly well but definitely has rough edges!

Contributions welcome:
- Bug fixes
- Feature improvements
- Better Mistral prompts (the genre filtering is an art!)
- Support for other LLMs (Llama, Qwen, etc.)

---

## 📜 License

MIT License - See [LICENSE](LICENSE) file

Built with ❤️ by Andrej & Irene at Alienish Games

---

## 🙏 Acknowledgments

- **Mutagen** - Audio metadata reading
- **Watchdog** - Filesystem monitoring
- **Ollama** - Local LLM runtime
- **Mistral AI** - The music knowledge brain
- **Claude (Anthropic)** - Pair programming partner who helped debug why Mistral kept putting Roxette in prog metal playlists 😄

---

## 💬 Contact

- Alienish Games: [Website](https://alienishgames.com)
- Andrej: [GitHub](https://github.com/YOUR_GITHUB)

*"Do you want to build a snowman?" - Mistral's idea of progressive metal* 🎵❄️
