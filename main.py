import asyncio
import os
from dataclasses import dataclass
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import yt_dlp

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing. Copy .env.example to .env and set it.")

intents = discord.Intents.default()

YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


@dataclass
class Track:
    title: str
    webpage_url: str
    stream_url: str
    requester: discord.Member


class MusicState:
    def __init__(self, guild_id: int) -> None:
        self.guild_id = guild_id
        self.queue: list[Track] = []
        self.current: Optional[Track] = None
        self.text_channel: Optional[discord.abc.Messageable] = None
        self.lock = asyncio.Lock()

    async def resolve_track(self, query: str, requester: discord.Member) -> Track:
        loop = asyncio.get_running_loop()

        def extract() -> dict:
            with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ytdl:
                result = ytdl.extract_info(query, download=False)
                if "entries" in result:
                    entries = [entry for entry in result["entries"] if entry]
                    if not entries:
                        raise ValueError("No results were found.")
                    return entries[0]
                return result

        info = await loop.run_in_executor(None, extract)
        stream_url = info.get("url")
        webpage_url = info.get("webpage_url") or query
        title = info.get("title") or "Unknown title"
        if not stream_url:
            raise ValueError("The audio stream could not be loaded.")
        return Track(title, webpage_url, stream_url, requester)

    async def play_next(self, voice_client: discord.VoiceClient) -> None:
        async with self.lock:
            if not self.queue:
                self.current = None
                return
            self.current = self.queue.pop(0)
            track = self.current

        source = discord.FFmpegPCMAudio(track.stream_url, **FFMPEG_OPTIONS)

        def finished(error: Optional[Exception]) -> None:
            if error:
                print(f"Playback error in guild {self.guild_id}: {error}")
            asyncio.run_coroutine_threadsafe(self.play_next(voice_client), bot.loop)

        voice_client.play(source, after=finished)
        if self.text_channel:
            await self.text_channel.send(f"▶️ Now playing **{track.title}**")


class MusicBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix="!", intents=intents)
        self.music_states: dict[int, MusicState] = {}

    def state_for(self, guild_id: int) -> MusicState:
        if guild_id not in self.music_states:
            self.music_states[guild_id] = MusicState(guild_id)
        return self.music_states[guild_id]

    async def setup_hook(self) -> None:
        await self.tree.sync()


bot = MusicBot()


def guild_state(interaction: discord.Interaction) -> Optional[MusicState]:
    if interaction.guild is None:
        return None
    return bot.state_for(interaction.guild.id)


def voice_channel_for(interaction: discord.Interaction) -> Optional[discord.VoiceChannel]:
    if not isinstance(interaction.user, discord.Member):
        return None
    if isinstance(interaction.user.voice, discord.VoiceState):
        return interaction.user.voice.channel
    return None


@bot.event
async def on_ready() -> None:
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")


@bot.tree.command(name="join", description="Join your current voice channel.")
async def join(interaction: discord.Interaction) -> None:
    channel = voice_channel_for(interaction)
    if channel is None:
        await interaction.response.send_message("Join a voice channel first.", ephemeral=True)
        return
    voice_client = interaction.guild.voice_client if interaction.guild else None
    if voice_client:
        await voice_client.move_to(channel)
    else:
        await channel.connect()
    state = guild_state(interaction)
    if state:
        state.text_channel = interaction.channel
    await interaction.response.send_message(f"Joined **{channel.name}**.")


@bot.tree.command(name="play", description="Play a YouTube URL or search query.")
@app_commands.describe(query="A song name, YouTube URL, or playlist-free video URL")
async def play(interaction: discord.Interaction, query: str) -> None:
    channel = voice_channel_for(interaction)
    if channel is None:
        await interaction.response.send_message("Join a voice channel first.", ephemeral=True)
        return
    await interaction.response.defer()
    state = guild_state(interaction)
    if state is None:
        await interaction.followup.send("This command can only be used in a server.")
        return
    state.text_channel = interaction.channel
    voice_client = interaction.guild.voice_client
    if voice_client is None:
        voice_client = await channel.connect()
    elif voice_client.channel != channel:
        await voice_client.move_to(channel)
    try:
        track = await state.resolve_track(query, interaction.user)
    except (ValueError, yt_dlp.utils.DownloadError) as error:
        await interaction.followup.send(f"Could not load that track: {error}")
        return
    state.queue.append(track)
    if voice_client.is_playing() or voice_client.is_paused():
        await interaction.followup.send(f"Queued **{track.title}** (position {len(state.queue)}).")
    else:
        await state.play_next(voice_client)
        await interaction.followup.send(f"Added **{track.title}** to playback.")


@bot.tree.command(name="skip", description="Skip the current track.")
async def skip(interaction: discord.Interaction) -> None:
    voice_client = interaction.guild.voice_client if interaction.guild else None
    if not voice_client or not voice_client.is_playing():
        await interaction.response.send_message("Nothing is playing.", ephemeral=True)
        return
    voice_client.stop()
    await interaction.response.send_message("Skipped the current track.")


@bot.tree.command(name="pause", description="Pause playback.")
async def pause(interaction: discord.Interaction) -> None:
    voice_client = interaction.guild.voice_client if interaction.guild else None
    if not voice_client or not voice_client.is_playing():
        await interaction.response.send_message("Nothing is playing.", ephemeral=True)
        return
    voice_client.pause()
    await interaction.response.send_message("Playback paused.")


@bot.tree.command(name="resume", description="Resume paused playback.")
async def resume(interaction: discord.Interaction) -> None:
    voice_client = interaction.guild.voice_client if interaction.guild else None
    if not voice_client or not voice_client.is_paused():
        await interaction.response.send_message("Playback is not paused.", ephemeral=True)
        return
    voice_client.resume()
    await interaction.response.send_message("Playback resumed.")


@bot.tree.command(name="queue", description="Show the current track queue.")
async def queue(interaction: discord.Interaction) -> None:
    state = guild_state(interaction)
    if state is None or (state.current is None and not state.queue):
        await interaction.response.send_message("The queue is empty.")
        return
    lines = []
    if state.current:
        lines.append(f"Now playing: **{state.current.title}**")
    lines.extend(f"{index}. {track.title}" for index, track in enumerate(state.queue, 1))
    await interaction.response.send_message("\n".join(lines[:25]))


@bot.tree.command(name="leave", description="Stop playback and leave the voice channel.")
async def leave(interaction: discord.Interaction) -> None:
    voice_client = interaction.guild.voice_client if interaction.guild else None
    if not voice_client:
        await interaction.response.send_message("I am not in a voice channel.", ephemeral=True)
        return
    state = guild_state(interaction)
    if state:
        state.queue.clear()
        state.current = None
    await voice_client.disconnect()
    await interaction.response.send_message("Left the voice channel and cleared the queue.")


bot.run(TOKEN)
