from bot_client import BotClient

if __name__ == "__main__":
    base_url = "http://localhost:3000/api/bots/4b4cbd72-0a3a-482d-86e2-ddac2e94445b"
    # base_url = "https://rnpmd-182-253-63-43.a.free.pinggy.link/api/bots/4b4cbd72-0a3a-482d-86e2-ddac2e94445b"
    bot_client = BotClient(base_url)

    if bot_client.join(preferred_board_id=2):
        bot_client.collect_all_diamonds()
    else:
        print("Failed to join the board.")




# base_url = "https://rngri-2404-8000-100b-82e-f845-7ffd-316e-7e74.a.free.pinggy.link/api/bots/4b4cbd72-0a3a-482d-86e2-ddac2e94445b"
