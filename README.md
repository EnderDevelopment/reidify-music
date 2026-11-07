# Discord Music Bot

Reidify is a Python Discord bot and music bot that searches YouTube or accepts YouTube URLs, streams audio through Discord voice channels with FFmpeg, and manages an independent playback queue for each server.

## Install

Requirements:

- Python 3.10 or newer
- FFmpeg installed and available on your system PATH
- A Discord application with a bot user
- Discord permissions: View Channel, Send Messages, Connect, and Speak
- The applications.commands scope enabled when inviting the bot

1. Clone or download the project.
2. Create and activate a virtual environment.
3. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env`.
5. Set `DISCORD_TOKEN` in `.env` to your Discord bot token. Do not commit the `.env` file.
6. Invite the bot to your server with the required permissions and the applications.commands scope.

## Use

Start the bot:

```bash
python main.py
```

Use these slash commands in a Discord server:

- `/join` — Join your current voice channel.
- `/play <query>` — Play a YouTube URL or search YouTube by song name.
- `/pause` — Pause the current playback.
- `/resume` — Resume paused playback.
- `/skip` — Skip the current track.
- `/queue` — Display the current track and queued tracks.
- `/leave` — Stop playback, clear the server queue, and leave the voice channel.

Before using `/play`, join a voice channel. The bot can also join your current voice channel automatically when `/play` is used. Each server has its own queue, and the queue is cleared when the bot leaves.

---

More Discord bot projects by EnderDevelopment: https://github.com/EnderDevelopment

Project page: https://dash.enderdevelopment.com/community/0a8747bd-7497-4a0b-a3e1-4abcb613c2cc?utm_source=github&utm_medium=readme&utm_campaign=auto_publish&utm_content=0a8747bd-7497-4a0b-a3e1-4abcb613c2cc
