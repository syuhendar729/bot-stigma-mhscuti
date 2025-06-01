from bot_client import BotClient

if __name__ == "__main__":
    base_url = "http://localhost:3000/api/bots/4b4cbd72-0a3a-482d-86e2-ddac2e94445b"
    bot_client = BotClient(base_url)

    if bot_client.join(preferred_board_id=1):
        bot_client.collect_all_diamonds()
    else:
        print("Failed to join the board.")
