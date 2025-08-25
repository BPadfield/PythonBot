import os, json, time, re
import discord
from llm_backends import LLM
import prompts  # your decider + responder prompt definitions

class DiscordAdapter:
    def __init__(self, bot_name: str, llm: LLM):
        self.bot_name = bot_name
        self.llm = llm
        self.history = []  # rolling chat buffer
        self.summary = None  # store summary if history is summarized
        self.last_reply_time = 0
        self.rate_limit = int(os.getenv("RATE_LIMIT_SECONDS", 20))
        intents = discord.Intents.default()
        intents.message_content = True
        self.client = discord.Client(intents=intents)
        self.allowed_channels = set(
            filter(None, os.getenv("DISCORD_ALLOWED_CHANNELS", "").split(','))
        )

    def summarize_history(self):
        # Use LLM to summarize the history
        if not self.history:
            return
        summary_prompt = prompts.summarize_prompt(self.bot_name, self.history)
        summary = self.llm.generate(
            prompts.SUMMARIZER_SYSTEM,
            summary_prompt,
            temperature=0.3
        )
        self.summary = summary
        self.history = []  # Clear history after summarizing

    def get_full_history(self):
        # Combine summary and current history for prompts
        if self.summary:
            return [f"Summary: {self.summary}"] + self.history
        return self.history

    def run(self):
        @self.client.event
        async def on_ready():
            print(f"[discord] Logged in as {self.client.user}")

        @self.client.event
        async def on_message(message: discord.Message):
            if message.author.bot:
                return

            content = message.content
            self.history.append(f"{message.author.name}: {content}")
            if len(self.history) > 20:
                self.summarize_history()

            # Rate limit
            if time.time() - self.last_reply_time < self.rate_limit:
                print(f"[discord] Rate limit exceeded")
                return

            # --- DECIDER PHASE ---
            decider_raw = self.llm.generate(
                prompts.DECIDER_SYSTEM,
                prompts.decider_prompt(self.bot_name, self.get_full_history()),
                temperature=0.3,
                model=os.getenv("LW_OLLAMA_MODEL", "gemma:3b")
            )
            try:
                decision = parse_json_block(decider_raw)
                
            except json.JSONDecodeError:
                print(f"[discord] Bad decision JSON: {decider_raw}")
                return

            if not decision.get("should_reply"):
                print(f"No reply needed, Reason: {decision.get('reason', 'Unknown')}")
                return

            # --- RESPONDER PHASE ---
            reply = self.llm.generate(
                prompts.RESPONDER_SYSTEM,
                prompts.responder_prompt(self.bot_name, decision["intent"], self.get_full_history()),
                temperature=0.7
            )

            await message.channel.send(reply)
            self.last_reply_time = time.time()
            self.history.append(f"{self.bot_name}: {reply}")

        self.client.run(os.getenv("DISCORD_TOKEN"))
def parse_json_block(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    raise ValueError("No JSON found")