import os, json, time
from dotenv import load_dotenv
from rich.console import Console
from llm_backends import make_llm
import prompts

load_dotenv()
console = Console()
llm = make_llm()

BOT_NAME = os.getenv("BOT_NAME", "@roomie")
rate_limit = int(os.getenv("RATE_LIMIT_SECONDS", "4"))
last_reply_time = 0
history = []
chat_adapter = os.getenv("CHAT_ADAPTER", "console").lower()
bot_name = os.getenv("BOT_NAME", "@roomie")

if chat_adapter == "discord":
    from discord_adapter import DiscordAdapter
    adapter = DiscordAdapter(bot_name, llm)
    adapter.run()
else:
    console.print("[bold green]Chat started. Type messages like 'Alice: hello'.[/]")

    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not line:
            continue

        history.append(line)
        if len(history) > 20:
            history = history[-20:]

        # Rate limit
        if time.time() - last_reply_time < rate_limit:
            continue

        # Decision phase
        decision_raw = llm.generate(prompts.DECIDER_SYSTEM, prompts.decider_prompt(BOT_NAME, history), temperature=0.3)
        try:
            decision = json.loads(decision_raw)
        except json.JSONDecodeError:
            console.print(f"[yellow]Bad decision JSON:[/] {decision_raw}")
            continue

        if not decision.get("should_reply"):
            continue

        # Response phase
        reply = llm.generate(prompts.RESPONDER_SYSTEM, prompts.responder_prompt(BOT_NAME, decision["intent"], history), temperature=0.7)
        console.print(f"[bold cyan]{BOT_NAME}[/]: {reply}")
        last_reply_time = time.time()
