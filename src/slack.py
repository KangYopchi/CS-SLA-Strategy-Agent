import os
from typing import Dict, cast

from langfuse.langchain import CallbackHandler
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler


class SlackBot:
    def __init__(
        self,
        bot_token: str,
        app_token: str,
        agent,
        target_boss_id: str | None = None,
        source_channel_id: str | None = None,
        target_channel_id: str | None = None,
        IDs: dict[str, str] | None = None,
    ) -> None:
        """
        Args:
            bot_token: Slack bot token
            agent: Agent instance
            target_boss_id: Target boss user ID
            source_channel_id: Source channel ID
            target_channel_id: Target channel ID
            IDs: Dictionary containing IDs
                - TARGET_BOSS_ID: Target boss user ID
                - SOURCE_CHANNEL_ID: Source channel ID
                - TARGET_CHANNEL_ID: Target channel ID
        """
        self.agent = agent
        self.app = App(token=bot_token)

        # 방법 1: 개별 파라미터로 전달된 경우
        if IDs is None:
            if (
                target_boss_id is None
                or source_channel_id is None
                or target_channel_id is None
            ):
                raise ValueError(
                    "IDs가 제공되지 않은 경우, target_boss_id, source_channel_id, target_channel_id를 모두 제공해야 합니다."
                )
            self.target_boss_id = target_boss_id
            self.source_channel_id = source_channel_id
            self.target_channel_id = target_channel_id
        # 방법 2: IDs 딕셔너리로 전달된 경우
        else:
            required_keys = ["TARGET_BOSS_ID", "SOURCE_CHANNEL_ID", "TARGET_CHANNEL_ID"]
            missing_keys = [key for key in required_keys if key not in IDs]
            if missing_keys:
                raise ValueError(
                    f"IDs 딕셔너리에 필수 키가 누락되었습니다: {missing_keys}"
                )
            self.target_boss_id = IDs["TARGET_BOSS_ID"]
            self.source_channel_id = IDs["SOURCE_CHANNEL_ID"]
            self.target_channel_id = IDs["TARGET_CHANNEL_ID"]

        self.app.command("/notification")(self.broadcast_command)

        self.app.event("message")(self.handle_message)

        self.handler = SocketModeHandler(self.app, app_token)

    def activate_slack_bot(self) -> None:
        self.handler.start()

    def get_report(self, text: str) -> dict[str, str]:
        spreadsheet_id: str | None = os.getenv("GOOGLE_SPREADSHEET_ID")

        if not spreadsheet_id:
            raise ValueError("GOOGLE_SPREADSHEET_ID is not set")

        sheet_name = "202501"

        input_data = {
            "spreadsheet_id": spreadsheet_id,
            "sheet_name": sheet_name,
            "customer_request": f"{text}",
            "condition": {
                "weather": "폭설",
                "event": "None",
                "attendance_rate": 0.6,
            },
        }

        langfuse_callback = CallbackHandler()

        result = self.agent.invoke(
            input_data, config={"callbacks": [langfuse_callback]}
        )

        return result

    def broadcast_command(self, ack, body, client):
        # (중요) 일단 "알겠습니다!" 하고 슬랙한테 신호 보내기 (안 하면 에러 남)
        ack()

        # 3. 누가, 어디서, 뭐라고 했는지 정보 꺼내기
        user_id = body["user_id"]
        channel_id = body["channel_id"]
        text = body["text"]  # "/공지 할말" 뒤에 쓴 "할말" 부분

        # 4. 검문 검색 🚧 (대장님인가? + 방송실인가?)
        if (user_id == self.target_boss_id) and (channel_id == self.source_channel_id):
            # input example

            result = self.get_report(text)

            report = cast(Dict, result["report"])

            # result = {"summary": "테스트", "urgency": "medium", "strategy": "high"}

            try:
                client.chat_postMessage(
                    channel=self.target_channel_id,
                    text=f"📢 [긴급 공지] \n\n summary:{report['summary']} \n\n 긴급도: {report['urgency']} \n\n 전략: {report['strategy']}",
                )

                # 5. 보고자에게 확인 사살 (Ephemeral)
                client.chat_postEphemeral(
                    channel=self.source_channel_id,
                    user=user_id,
                    text="✅ 공지가 성공적으로 전송되었습니다.",
                )
            except Exception as e:
                print(f"전송 실패: {e}")

        else:
            # 권한이 없는 경우
            client.chat_postMessage(
                channel=self.source_channel_id,
                user=user_id,
                text="🚫 당신은 공지를 보낼 권한이 없거나, 올바른 방이 아닙니다.",
            )

    def handle_message(self, event, say):
        if event.get("bot_id"):
            return
