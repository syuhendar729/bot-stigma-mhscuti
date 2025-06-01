import requests
import time
import json
import copy
import os
import random

class BotClient:
    def __init__(self, api_base_url, bot_id, move_delay=0.2):
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
        self.log_file_path = "Randy/bot_log.txt"
        self.home_position = None  # Store spawn position
        self.diamond_visits = 0    # Track diamond visits
        self.move_delay = move_delay  # Configurable move delay
        self.cache = {}  # For caching pathfinding results
        self.diamond_targets_history = set()  # Track diamonds we've targeted
        self.minimum_server_delay = 0.1  # Will be updated from server
        
        os.makedirs("Randy", exist_ok=True)
        with open(self.log_file_path, "a") as log_file:
            log_file.write(f"\n\n--- Bot Session Started at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")

    def join(self, preferred_board_id=9):
        url = f"{self.base_url}/join"
        payload = {
            "preferredBoardId": preferred_board_id,
            "name": self.my_name  # Make sure name is being sent properly
        }
        response = requests.post(url, json=payload, headers=self.headers)
        print(f"Join response: {response.status_code}")
        
        try:
            data = response.json()
            if "statusCode" in data and data["statusCode"] >= 400:
                print("Error joining game:", data)
                return False
            
            # Process initial game state
            print(json.dumps(data, indent=4))
            self.game_objects = data.get("gameObjects", [])
            bot_obj = self.find_bot()
            
            # Make sure the bot ID is properly stored from the server response
            for obj in self.game_objects:
                if obj.get("type") == "BotGameObject" and obj.get("properties", {}).get("name") == self.my_name:
                    self.bot_id = obj.get("id")  # Update bot_id from server
                    print(f"Updated bot ID to: {self.bot_id}")
                    break
            
            # Store spawn/home position
            if self.bot_position:
                self.home_position = copy.deepcopy(self.bot_position)
                print(f"Home position set to: {self.home_position}")
                with open(self.log_file_path, "a") as log_file:
                    log_file.write(f"Home position: ({self.home_position['x']}, {self.home_position['y']})\n")
            
            # Analyze diamonds in the initial state
            diamonds = self.get_diamonds()
            total_diamonds, high_value_diamonds = self.count_diamonds()
            
            print(f"Initial state: Found {total_diamonds} diamonds ({high_value_diamonds} high-value)")
            
            # Log all diamond positions
            with open(self.log_file_path, "a") as log_file:
                log_file.write(f"--- Initial board state ---\n")
                log_file.write(f"Total diamonds: {total_diamonds} (high value: {high_value_diamonds})\n")
                
                # Sort diamonds by value and distance
                sorted_diamonds = sorted(diamonds, key=lambda d: (-d.get('points', 1), d.get('distance', 999)))
                
                for i, diamond in enumerate(sorted_diamonds):
                    points = diamond.get('points', 1)
                    pos = diamond.get('position', {})
                    distance = diamond.get('distance', 'unknown')
                    log_file.write(f"Diamond {i+1}: {points} points at ({pos.get('x')},{pos.get('y')}) - distance: {distance}\n")
            
            # Also display teleporters
            teleporters = self.get_teleporters()
            if teleporters:
                print(f"Found {len(teleporters)} teleporters")
                for tp in teleporters:
                    pos = tp.get('position', {})
                    pair_id = tp.get('pairId', 'unknown')
                    print(f"Teleporter with ID {pair_id} at ({pos.get('x')},{pos.get('y')})")
                    
            # Check for diamond button
            diamond_button = self.get_diamond_button()
            if diamond_button:
                pos = diamond_button.get('position', {})
                print(f"Diamond button found at ({pos.get('x')},{pos.get('y')})")
            
            # Find base position
            base_obj = self.get_my_base()
            if base_obj:
                pos = base_obj.get('position', {})
                print(f"Base located at ({pos.get('x')},{pos.get('y')})")
                
            return True
        except Exception as e:
            print(f"Exception during join: {e}")
            print(response.text)
            return False

    def find_bot(self):
        # Cari bot kita sendiri dan simpan posisi
        for obj in self.game_objects:
            if obj.get("type") == "BotGameObject":
                self.bot_position = obj.get("position")
                self.my_name = obj.get("properties", {}).get("name", self.my_name)
                
                # Log inventory details
                if "properties" in obj and "inventory" in obj["properties"]:
                    inventory = obj["properties"]["inventory"]
                    print(f"Bot inventory: {len(inventory)} items: {inventory}")
                
                print(f"Bot found at position: {self.bot_position} with name: {self.my_name}")
                return obj
        print("Bot not found in game objects.")
        self.bot_position = None
        return None

    def get_my_base(self):
        # Cari base bot
        for obj in self.game_objects:
            if obj.get("type") == "BaseGameObject" and "properties" in obj:
                if obj["properties"].get("ownerId") == self.bot_id:
                    return obj
        return None

    def get_inventory_info(self):
        # Get inventory count and size
        bot_obj = self.find_bot()
        if bot_obj and "properties" in bot_obj:
            inventory_size = bot_obj["properties"].get("inventorySize", 5)
            inventory_count = 0
            if "inventory" in bot_obj["properties"]:
                inventory_count = len(bot_obj["properties"]["inventory"])
            return inventory_count, inventory_size
        return 0, 5

    @staticmethod
    def manhattan_distance(p1, p2):
        return abs(p1['x'] - p2['x']) + abs(p1['y'] - p2['y'])

    def get_diamonds(self):
        diamonds = []
        for obj in self.game_objects:
            if obj.get("type") == "DiamondGameObject":
                points = obj.get("properties", {}).get("points", 1)
                diamonds.append({
                    "id": obj["id"],
                    "position": obj["position"],
                    "points": points,
                    "distance": self.manhattan_distance(self.bot_position, obj["position"]),
                    "type": "DiamondGameObject",
                    "is_red": points > 1
                })
        return diamonds

    def get_diamond_button(self):
        for obj in self.game_objects:
            if obj.get("type") == "DiamondButtonGameObject":
                return {
                    "id": obj["id"],
                    "position": obj["position"],
                    "distance": self.manhattan_distance(self.bot_position, obj["position"]),
                    "type": "DiamondButtonGameObject"
                }
        return None

    def get_teleporters(self):
        teleporters = []
        for obj in self.game_objects:
            if obj.get("type") == "TeleportGameObject":
                teleporters.append({
                    "id": obj["id"],
                    "position": obj["position"],
                    "pairId": obj.get("properties", {}).get("pairId", ""),
                    "distance": self.manhattan_distance(self.bot_position, obj["position"]),
                    "type": "TeleportGameObject"
                })
        return teleporters

    def count_diamonds(self):
        total = 0
        high_value = 0
        for obj in self.game_objects:
            if obj.get("type") == "DiamondGameObject":
                total += 1
                points = obj.get("properties", {}).get("points", 1)
                if points > 1:
                    high_value += 1
        return total, high_value

    def is_diamond_at_position(self, position):
        for obj in self.game_objects:
            if obj.get("type") == "DiamondGameObject" and obj.get("position", {}).get("x") == position["x"] and obj.get("position", {}).get("y") == position["y"]:
                return True
        return False

    def is_tile_walkable(self, position):
        for obj in self.game_objects:
            if obj.get("type") == "WallGameObject" and obj.get("position", {}).get("x") == position["x"] and obj.get("position", {}).get("y") == position["y"]:
                return False
        return True

    def a_star_path(self, start, goal):
        """A* pathfinding algorithm implementation"""
        # Priority queue for open nodes
        open_set = []
        # Dict to store the cost from start to each node
        g_score = {f"{start['x']},{start['y']}": 0}
        # Dict to store estimated total cost from start to goal through node
        f_score = {f"{start['x']},{start['y']}": self.manhattan_distance(start, goal)}
        
        # Add start point to open set with its f_score as priority
        import heapq
        heapq.heappush(open_set, (f_score[f"{start['x']},{start['y']}"], f"{start['x']},{start['y']}"))
        
        # Dict to store the most efficient previous step
        came_from = {}
        
        while open_set:
            # Get node with lowest f_score
            _, current = heapq.heappop(open_set)
            x, y = map(int, current.split(','))
            current_pos = {'x': x, 'y': y}
            
            # If reached goal, construct the path
            if x == goal['x'] and y == goal['y']:
                path = []
                while current in came_from:
                    prev = came_from[current]
                    prev_x, prev_y = map(int, prev.split(','))
                    
                    # Determine direction
                    if prev_x < x:
                        path.append("EAST")
                    elif prev_x > x:
                        path.append("WEST")
                    elif prev_y < y:
                        path.append("SOUTH")
                    elif prev_y > y:
                        path.append("NORTH")
                        
                    current = prev
                    x, y = prev_x, prev_y
                
                # Reverse to get from start to goal
                path.reverse()
                return path
            
            # Check all valid neighbors
            neighbors = [
                ("EAST", {'x': x + 1, 'y': y}),
                ("WEST", {'x': x - 1, 'y': y}),
                ("SOUTH", {'x': x, 'y': y + 1}),
                ("NORTH", {'x': x, 'y': y - 1})
            ]
            
            # Filter out unwalkable tiles
            neighbors = [n for n in neighbors if self.is_tile_walkable(n[1])]
            
            for _, neighbor in neighbors:
                neighbor_str = f"{neighbor['x']},{neighbor['y']}"
                
                # Calculate tentative g_score
                tentative_g_score = g_score[f"{x},{y}"] + 1
                
                # If this path to neighbor is better than previous one
                if neighbor_str not in g_score or tentative_g_score < g_score[neighbor_str]:
                    # Record this path
                    came_from[neighbor_str] = f"{x},{y}"
                    g_score[neighbor_str] = tentative_g_score
                    f_score[neighbor_str] = tentative_g_score + self.manhattan_distance(neighbor, goal)
                    
                    # Add to open set if not already in
                    if not any(neighbor_str == item[1] for item in open_set):
                        heapq.heappush(open_set, (f_score[neighbor_str], neighbor_str))
        
        # If no path found, return empty list
        print("No path found with A* algorithm")
        return []

    # Replace path_to_target with this improved version
    def path_to_target(self, start, target):
        # Try A* algorithm first
        path = self.a_star_path(start, target)
        if path:
            return path
            
        # Fall back to simple path if A* fails
        print("Falling back to simple pathfinding")
        directions = []
        x, y = start['x'], start['y']
        tx, ty = target['x'], target['y']
        
        # Simple direction generation that avoids obstacles
        while x != tx or y != ty:
            possible_moves = []
            
            if x < tx:
                possible_moves.append(("EAST", {"x": x+1, "y": y}))
            elif x > tx:
                possible_moves.append(("WEST", {"x": x-1, "y": y}))
                
            if y < ty:
                possible_moves.append(("SOUTH", {"x": x, "y": y+1}))
            elif y > ty:
                possible_moves.append(("NORTH", {"x": x, "y": y-1}))
                
            # Filter out unwalkable tiles
            possible_moves = [move for move in possible_moves if self.is_tile_walkable(move[1])]
            
            if not possible_moves:
                # No direct path, try alternate directions
                alternate_directions = []
                if x != tx:  # Try moving vertically first if horizontal path is blocked
                    if self.is_tile_walkable({"x": x, "y": y-1}):
                        alternate_directions.append(("NORTH", {"x": x, "y": y-1}))
                    if self.is_tile_walkable({"x": x, "y": y+1}):
                        alternate_directions.append(("SOUTH", {"x": x, "y": y+1}))
                else:  # Try moving horizontally if vertical path is blocked
                    if self.is_tile_walkable({"x": x-1, "y": y}):
                        alternate_directions.append(("WEST", {"x": x-1, "y": y}))
                    if self.is_tile_walkable({"x": x+1, "y": y}):
                        alternate_directions.append(("EAST", {"x": x+1, "y": y}))
                
                if alternate_directions:
                    possible_moves = [random.choice(alternate_directions)]
                else:
                    print("No valid path found to target!")
                    break
                
            # Choose the move
            move, new_pos = possible_moves[0]
            directions.append(move)
            x, y = new_pos["x"], new_pos["y"]
            
        return directions

    def move(self, direction):
        url = f"{self.base_url}/move"
        payload = {
            "direction": direction,
            "botId": self.bot_id  # Include your bot ID in every move
        }
        response = requests.post(url, json=payload, headers=self.headers)
        
        try:
            data = response.json()
            
            # Check if we're about to step on a diamond
            expected_pos = copy.deepcopy(self.bot_position)
            if direction == "NORTH": expected_pos["y"] -= 1
            elif direction == "SOUTH": expected_pos["y"] += 1
            elif direction == "EAST": expected_pos["x"] += 1
            elif direction == "WEST": expected_pos["x"] -= 1
            
            # Track if we're stepping on a diamond
            was_diamond = self.is_diamond_at_position(expected_pos)
            if was_diamond:
                print(f"About to collect diamond at {expected_pos}")
            
            # Important: Update game objects from response first
            self.game_objects = data.get("gameObjects", [])
            # Then find bot to update position AND inventory data
            bot_obj = self.find_bot()
            
            # Get updated inventory info directly from game state
            inventory_count, inventory_size = self.get_inventory_info()
            
            # If we collected a diamond, increment the counter
            if was_diamond:
                self.diamond_visits += 1
                print(f"Diamond collected! Count: {self.diamond_visits}/5")
            
            with open(self.log_file_path, "a") as log_file:
                log_file.write(f"{time.strftime('%H:%M:%S')} - Move {direction} - Pos: {self.bot_position} - Inventory: {inventory_count}/{inventory_size}")
                if was_diamond:
                    log_file.write(f" - Diamond collected ({self.diamond_visits}/5)")
                log_file.write("\n")
            
            return True if "gameObjects" in data else False
        except Exception as e:
            print(f"Move failed: {e}")
            return False

    def calculate_greedy_value(self, item, inventory_count, inventory_size, has_red_button=False):
        distance = self.manhattan_distance(self.bot_position, item['position'])
        
        # If we've visited 5 diamonds, prioritize returning home
        if self.diamond_visits >= 5 and item.get('is_home', False):
            return 200 / (distance + 1)
        
        if item['type'] == 'DiamondGameObject':
            points = item.get('points', 1)
            # Prioritize high-value diamonds more strongly
            if points > 1:
                return (10 * points) / (distance + 1)
            return 2.0 / (distance + 1)
        
        elif item['type'] == 'DiamondButtonGameObject':
            if has_red_button:
                return 7 / (distance + 1)
            return 0
        
        elif item['type'] == 'BaseGameObject':
            if inventory_count >= inventory_size:
                return 100 / (distance + 1)
            elif inventory_count > 0:
                return (inventory_count * 3) / (distance + 1)
            return 0
        
        elif item['type'] == 'TeleportGameObject':
            return 1 / (distance + 1)
        
        return 0

    def follow_path(self, directions):
        current_pos = copy.deepcopy(self.bot_position)
        previous_pos = current_pos
        
        for direction in directions:
            # Check if we're about to step on a diamond
            expected_pos = copy.deepcopy(self.bot_position)
            if direction == "NORTH": expected_pos["y"] -= 1
            elif direction == "SOUTH": expected_pos["y"] += 1
            elif direction == "EAST": expected_pos["x"] += 1
            elif direction == "WEST": expected_pos["x"] -= 1
            
            if self.is_diamond_at_position(expected_pos):
                print(f"About to collect diamond at {expected_pos}")
            
            if not self.move(direction):
                return False
            
            # Check for teleportation by comparing expected position to actual position
            new_pos = self.bot_position
            expected_pos = copy.deepcopy(previous_pos)
            if direction == "NORTH": expected_pos["y"] -= 1
            elif direction == "SOUTH": expected_pos["y"] += 1
            elif direction == "EAST": expected_pos["x"] += 1
            elif direction == "WEST": expected_pos["x"] -= 1
            
            # If actual position is far from expected, we teleported
            if self.manhattan_distance(expected_pos, new_pos) > 1:
                print(f"Teleportation detected from {previous_pos} to {new_pos}")
            
            previous_pos = copy.deepcopy(new_pos)
            time.sleep(0.5)
        
        return True

    def run_bot(self):
        last_positions = []
        stuck_counter = 0
        MAX_STUCK_COUNT = 3
        game_active = True
        
        # Add a global stuck detection
        global_stuck_counter = 0
        last_five_targets = []
        
        while game_active:
            # Check if bot is stuck
            if last_positions and all(self.manhattan_distance(pos, self.bot_position) == 0 for pos in last_positions[-3:]):
                stuck_counter += 1
                print(f"Bot appears to be stuck (counter: {stuck_counter})")
                
                if stuck_counter >= MAX_STUCK_COUNT:
                    print("Attempting to break out of stuck state")
                    diamond_button = self.get_diamond_button()
                    base_obj = self.get_my_base()
                    inventory_count, _ = self.get_inventory_info()
                    
                    if diamond_button:
                        print("Moving to diamond button to break stuck state")
                        steps = self.path_to_target(self.bot_position, diamond_button["position"])
                        self.follow_path(steps)
                    elif base_obj and inventory_count > 0:
                        print("Moving to base to break stuck state")
                        steps = self.path_to_target(self.bot_position, base_obj["position"])
                        self.follow_path(steps)
                    else:
                        # Try random movements to break the loop
                        print("Using random movements to break stuck state")
                        for _ in range(3):
                            random_dir = random.choice(["NORTH", "SOUTH", "EAST", "WEST"])
                            self.move(random_dir)
                    
                    stuck_counter = 0
                    last_positions = []
            
            # Update position history
            if len(last_positions) >= 5:
                last_positions.pop(0)
            last_positions.append(copy.deepcopy(self.bot_position))
            
            # Get current inventory and objects
            inventory_count, inventory_size = self.get_inventory_info()
            diamonds = self.get_diamonds()
            teleporters = self.get_teleporters()
            diamond_button = self.get_diamond_button()
            base_obj = self.get_my_base()
            
            total_diamonds, high_value_diamonds = self.count_diamonds()
            
            print(f"Current state: Inventory {inventory_count}/{inventory_size}, Diamonds: {total_diamonds} (high value: {high_value_diamonds}), Diamond visits: {self.diamond_visits}/5")
            
            # Determine potential targets
            potential_targets = []
            
            # Check if we should return home after visiting 5 diamonds
            if self.diamond_visits >= 5 and self.home_position:
                print(f"Visited 5 diamonds - returning to home at {self.home_position}")
                home_target = {
                    "id": "home",
                    "position": self.home_position,
                    "type": "HomePosition",
                    "is_home": True,
                    "distance": self.manhattan_distance(self.bot_position, self.home_position),
                    "greedy_value": 200 / (self.manhattan_distance(self.bot_position, self.home_position) + 1)
                }
                potential_targets.append(home_target)
            # Normal targeting logic
            elif inventory_count >= inventory_size and base_obj:
                print("Inventory full - prioritizing base")
                base_obj["greedy_value"] = 100
                potential_targets.append(base_obj)
            else:
                if inventory_count < inventory_size and diamonds:
                    print(f"Adding {len(diamonds)} diamonds as potential targets")
                    potential_targets.extend(diamonds)
                
                if base_obj and inventory_count > 0:
                    print("Adding base as potential target")
                    potential_targets.append(base_obj)
                
                if diamond_button and (total_diamonds < 10 or high_value_diamonds < 3):
                    print("Adding diamond button as potential target")
                    potential_targets.append(diamond_button)
                
                if teleporters:
                    print(f"Adding {len(teleporters)} teleporters as potential targets")
                    potential_targets.extend(teleporters)
                
                if not potential_targets and inventory_count > 0 and base_obj:
                    print("No primary targets - adding base due to having items in inventory")
                    potential_targets.append(base_obj)
                
                if not potential_targets and diamond_button:
                    print("No primary targets - adding diamond button as fallback")
                    potential_targets.append(diamond_button)

            # Calculate value for each target (except for home which is already calculated)
            if not (inventory_count >= inventory_size and base_obj) and not (self.diamond_visits >= 5 and self.home_position):
                for target in potential_targets:
                    if not target.get('is_home', False):  # Skip home target
                        has_red_button = (diamond_button is not None)
                        target["greedy_value"] = self.calculate_greedy_value(
                            target, inventory_count, inventory_size, has_red_button
                        )
            
            # Sort targets by value
            potential_targets.sort(key=lambda t: t.get("greedy_value", 0), reverse=True)
            
            if not potential_targets:
                print("No potential targets available - ending bot run")
                game_active = False
                break
                
            best_target = potential_targets[0]
            print(f"Selected target: {best_target.get('type')} at position {best_target.get('position')} with value {best_target.get('greedy_value')}")
            steps = self.path_to_target(self.bot_position, best_target["position"])
            
            if not steps:
                print("No path to target found - trying another target")
                if len(potential_targets) > 1:
                    best_target = potential_targets[1]
                    print(f"Selected alternate target: {best_target.get('type')}")
                    steps = self.path_to_target(self.bot_position, best_target["position"])
                else:
                    # No viable paths, try random movement
                    print("No alternate targets - using random movement")
                    random_dir = random.choice(["NORTH", "SOUTH", "EAST", "WEST"])
                    self.move(random_dir)
                    continue
            
            if not self.follow_path(steps):
                print("Failed to follow path - bot might be blocked")
                game_active = False
                break

            # If we reached home after 5 diamond visits, reset the counter
            if self.diamond_visits >= 5 and self.home_position and self.bot_position and \
               self.bot_position.get('x') == self.home_position.get('x') and \
               self.bot_position.get('y') == self.home_position.get('y'):
                print("Reached home after visiting 5 diamonds - resetting counter")
                self.diamond_visits = 0

            # Check if we're repeatedly targeting the same objects
            if len(last_five_targets) >= 5:
                if len(set(last_five_targets)) <= 2:  # Only 1-2 unique targets in last 5 moves
                    global_stuck_counter += 1
                    print(f"Global stuck detection: counter at {global_stuck_counter}")
                    if global_stuck_counter > 3:
                        print("Bot appears to be in a larger pattern loop - exploring randomly")
                        # Try some random movement to break out
                        for _ in range(3):
                            random_dir = random.choice(["NORTH", "SOUTH", "EAST", "WEST"])
                            self.move(random_dir)
                        global_stuck_counter = 0
                        last_five_targets = []
                else:
                    global_stuck_counter = 0
            
            if best_target:
                last_five_targets.append(best_target.get("id", "unknown"))
                if len(last_five_targets) > 5:
                    last_five_targets.pop(0)

def main():
    # Update API URL if needed
    API_BASE_URL = "https://rngjb-182-253-63-43.a.free.pinggy.link/api"
    BOT_ID = "9f7b0386-0bbd-4438-b3a5-7c253f0f8f88"
    
    # Initialize the bot client
    bot = BotClient(API_BASE_URL, BOT_ID)
    
    # Get bot info
    bot_response = requests.get(f"{API_BASE_URL}/bots/{BOT_ID}", headers=bot.headers)
    try:
        bot_data = bot_response.json()
        bot.my_name = bot_data.get("name", "randyGG")
    except Exception:
        pass
    
    # Get board info
    boards_response = requests.get(f"{API_BASE_URL}/boards", headers=bot.headers)
    board_id = 9
    try:
        boards_data = boards_response.json()
        if boards_data and len(boards_data) > 0:
            board_id = boards_data[0].get("id", 9)
    except Exception:
        pass
    
    # Join the game
    success = bot.join(board_id)
    if success:
        # Run the bot
        bot.run_bot()

if __name__ == "__main__":
    main()