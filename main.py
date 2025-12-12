import asyncio
import os

from dotenv import load_dotenv
from langgraph.graph.state import CompiledStateGraph

from src.agent import create_graph
from src.slack import SlackBot


def main() -> None:
    graph: CompiledStateGraph = create_graph()

    load_dotenv()

    IDs = {
        "TARGET_BOSS_ID": os.getenv("TARGET_BOSS_ID"),
        "SOURCE_CHANNEL_ID": os.getenv("SOURCE_CHANNEL_ID"),
        "TARGET_CHANNEL_ID": os.getenv("TARGET_CHANNEL_ID"),
    }

    bot_token = os.getenv("SLACK_BOT_TOKEN")
    app_token = os.getenv("SLACK_APP_TOKEN")

    print(f"IDs: {IDs} \n\n bot_token: {bot_token} app_token: {app_token}")

    slack_bot = SlackBot(
        bot_token=bot_token,
        app_token=app_token,
        agent=graph,
        IDs=IDs,
    )

    slack_bot.activate_slack_bot()


if __name__ == "__main__":
    main()


#  슬랙에서 입력을 받는다 -> 입력을 Agent에 전달한다 -> Agent가 Report를 생성한다 -> Report를 슬랙에 전달한다
