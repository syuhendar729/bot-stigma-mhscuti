import requests
import time
import json
import os
import msvcrt  # Windows-specific module for keyboard input
import sys
import colorama
from colorama import Fore, Back, Style

# Initialize colorama for colored console output
colorama.init()

class ManualController:
    def __init__(self, api_base_url, bot_id):
        self.base_url = f"{api_base_url}/bots/{bot_id}"
        self.api_base_url = api_base_url
        self.bot_id = bot_id
        self.headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }
        self.bot_position = None
        self.game_objects = []
        self.my_name = "randyGG"
        self.log_file_path = "Randy/manual_control_log.txt"
        
        os.makedirs("Randy", exist_ok=True)
        with open(self.log_file_path, "a") as log_file:
            log_file.write(f"\n\n--- Manual Control Session Started at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")

    def join(self, preferred_board_id=9):
        url = f"{self.base_url}/join"
        payload = {
            "preferredBoardId": preferred_board_id,
            "name": self.my_name
        }
        response = requests.post(url, json=payload, headers=self.headers)
        print(f"{Fore.CYAN}Join response: {response.status_code}{Style.RESET_ALL}")
        
        try:
            data = response.json()
            if "statusCode" in data and data["statusCode"] >= 400:
                print(f"{Fore.RED}Error joining game: {data}{Style.RESET_ALL}")
                return False
            
            # Process initial game state
            self.game_objects = data.get("gameObjects", [])
            self.find_bot()
            
            # Print the board
            self.print_board(data.get("width", 15), data.get("height", 15))
            
            print(f"{Fore.GREEN}Successfully joined the game!{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Board ID: {preferred_board_id}{Style.RESET_ALL}")
            
            return True
        except Exception as e:
            print(f"{Fore.RED}Exception during join: {e}{Style.RESET_ALL}")
            return False

    def find_bot(self):
        for obj in self.game_objects:
            if obj.get("type") == "BotGameObject":
                self.bot_position = obj.get("position")
                self.my_name = obj.get("properties", {}).get("name", self.my_name)
                
                # Get inventory info
                inventory_count = 0
                inventory_size = 5
                if "properties" in obj:
                    inventory_size = obj["properties"].get("inventorySize", 5)
                    if "inventory" in obj["properties"]:
                        inventory_count = len(obj["properties"]["inventory"])
                
                print(f"{Fore.YELLOW}Bot found at position: ({self.bot_position['x']}, {self.bot_position['y']}) with name: {self.my_name}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Inventory: {inventory_count}/{inventory_size}{Style.RESET_ALL}")
                return obj
        print(f"{Fore.RED}Bot not found in game objects.{Style.RESET_ALL}")
        self.bot_position = None
        return None

    def update_game_state(self):
        url = f"{self.base_url}"
        response = requests.get(url, headers=self.headers)
        
        try:
            data = response.json()
            self.game_objects = data.get("gameObjects", [])
            self.find_bot()
            return True
        except Exception as e:
            print(f"{Fore.RED}Error updating game state: {e}{Style.RESET_ALL}")
            return False

    def move(self, direction):
        url = f"{self.base_url}/move"
        payload = {"direction": direction}
        response = requests.post(url, json=payload, headers=self.headers)
        
        try:
            data = response.json()
            self.game_objects = data.get("gameObjects", [])
            bot_obj = self.find_bot()
            
            with open(self.log_file_path, "a") as log_file:
                log_file.write(f"{time.strftime('%H:%M:%S')} - Move {direction} - Pos: {self.bot_position}\n")
            
            return True if bot_obj else False
        except Exception as e:
            print(f"{Fore.RED}Move failed: {e}{Style.RESET_ALL}")
            return False

    def print_board(self, width=15, height=15):
        """Print the current state of the board"""
        # Create an empty board
        board = [[' ' for _ in range(width)] for _ in range(height)]
        
        # Fill in objects
        for obj in self.game_objects:
            if not obj.get("position"):
                continue
                
            x = obj.get("position").get("x", 0)
            y = obj.get("position").get("y", 0)
            
            if x >= width or y >= height or x < 0 or y < 0:
                continue
                
            object_type = obj.get("type")
            
            if object_type == "BotGameObject" and obj.get("properties", {}).get("name") == self.my_name:
                board[y][x] = f"{Fore.GREEN}B{Style.RESET_ALL}"  # Our bot
            elif object_type == "BotGameObject":
                board[y][x] = f"{Fore.RED}E{Style.RESET_ALL}"    # Enemy bot
            elif object_type == "WallGameObject":
                board[y][x] = f"{Fore.WHITE}#{Style.RESET_ALL}"  # Wall
            elif object_type == "DiamondGameObject":
                points = obj.get("properties", {}).get("points", 1)
                if points > 1:
                    board[y][x] = f"{Fore.RED}D{Style.RESET_ALL}"  # Red diamond
                else:
                    board[y][x] = f"{Fore.CYAN}d{Style.RESET_ALL}"  # Normal diamond
            elif object_type == "BaseGameObject":
                if obj.get("properties", {}).get("ownerId") == self.bot_id:
                    board[y][x] = f"{Fore.GREEN}H{Style.RESET_ALL}"  # Home base
                else:
                    board[y][x] = f"{Fore.YELLOW}h{Style.RESET_ALL}"  # Other base
            elif object_type == "DiamondButtonGameObject":
                board[y][x] = f"{Fore.MAGENTA}*{Style.RESET_ALL}"  # Diamond button
            elif object_type == "TeleportGameObject":
                board[y][x] = f"{Fore.BLUE}T{Style.RESET_ALL}"  # Teleporter
        
        # Print the board with coordinates
        print(f"\n{Fore.YELLOW}Current Board State:{Style.RESET_ALL}")
        print("  " + "".join(f"{i:2}" for i in range(width)))
        
        for y in range(height):
            print(f"{y:2}", end=" ")
            for x in range(width):
                print(board[y][x], end=" ")
            print()
        print()
        
        # Print legend
        print(f"{Fore.GREEN}B{Style.RESET_ALL} - Your bot   {Fore.RED}E{Style.RESET_ALL} - Enemy bot   {Fore.WHITE}#{Style.RESET_ALL} - Wall")
        print(f"{Fore.CYAN}d{Style.RESET_ALL} - Diamond     {Fore.RED}D{Style.RESET_ALL} - Red Diamond  {Fore.GREEN}H{Style.RESET_ALL} - Home base")
        print(f"{Fore.MAGENTA}*{Style.RESET_ALL} - Button      {Fore.BLUE}T{Style.RESET_ALL} - Teleporter")
        print()

    def display_help(self):
        print(f"\n{Fore.CYAN}=== WASD MANUAL CONTROLLER HELP ==={Style.RESET_ALL}")
        print(f"{Fore.WHITE}W{Style.RESET_ALL} - Move UP (NORTH)")
        print(f"{Fore.WHITE}A{Style.RESET_ALL} - Move LEFT (WEST)")
        print(f"{Fore.WHITE}S{Style.RESET_ALL} - Move DOWN (SOUTH)")
        print(f"{Fore.WHITE}D{Style.RESET_ALL} - Move RIGHT (EAST)")
        print(f"{Fore.WHITE}R{Style.RESET_ALL} - Refresh board view")
        print(f"{Fore.WHITE}H{Style.RESET_ALL} - Show this help")
        print(f"{Fore.WHITE}Q{Style.RESET_ALL} - Quit")
        print()

    def run_controller(self):
        """Run the manual controller using WASD keys"""
        self.display_help()
        
        while True:
            # Check if the keyboard has been hit
            if msvcrt.kbhit():
                key = msvcrt.getch().decode('utf-8').lower()
                
                if key == 'w':
                    print("Moving NORTH...")
                    self.move("NORTH")
                    self.print_board()
                elif key == 'a':
                    print("Moving WEST...")
                    self.move("WEST") 
                    self.print_board()
                elif key == 's':
                    print("Moving SOUTH...")
                    self.move("SOUTH")
                    self.print_board()
                elif key == 'd':
                    print("Moving EAST...")
                    self.move("EAST")
                    self.print_board()
                elif key == 'r':
                    print("Refreshing board...")
                    self.update_game_state()
                    self.print_board()
                elif key == 'h':
                    self.display_help()
                elif key == 'q':
                    print(f"{Fore.YELLOW}Exiting manual control...{Style.RESET_ALL}")
                    return
                
                # Small delay to avoid spamming the API
                time.sleep(0.1)

def main():
    # Use the same API URL and bot ID as botrandy.py
    API_BASE_URL = "https://rndyd-2404-8000-100b-82e-f845-7ffd-316e-7e74.a.free.pinggy.link/api"
    BOT_ID = "9f7b0386-0bbd-4438-b3a5-7c253f0f8f88"
    
    print(f"{Fore.CYAN}=== BOT MANUAL CONTROLLER ==={Style.RESET_ALL}")
    print(f"API URL: {API_BASE_URL}")
    print(f"Bot ID: {BOT_ID}")
    
    # Initialize the controller
    controller = ManualController(API_BASE_URL, BOT_ID)
    
    # Get board info
    boards_response = requests.get(f"{API_BASE_URL}/boards", headers=controller.headers)
    board_id = 9
    try:
        boards_data = boards_response.json()
        if boards_data and len(boards_data) > 0:
            print(f"\nAvailable boards:")
            for i, board in enumerate(boards_data):
                print(f"  {i+1}. Board ID {board.get('id')}")
            
            selection = input("\nSelect a board (or press Enter for default): ")
            if selection.isdigit() and 0 < int(selection) <= len(boards_data):
                board_id = boards_data[int(selection)-1].get('id')
            else:
                board_id = boards_data[0].get('id')
    except Exception as e:
        print(f"{Fore.RED}Error getting boards: {e}. Using default board ID: {board_id}{Style.RESET_ALL}")
    
    # Join the game
    success = controller.join(board_id)
    if success:
        print(f"{Fore.GREEN}Successfully joined the game! Use WASD to control your bot.{Style.RESET_ALL}")
        # Run the manual controller
        controller.run_controller()
    else:
        print(f"{Fore.RED}Failed to join the game.{Style.RESET_ALL}")

if __name__ == "__main__":
    main()