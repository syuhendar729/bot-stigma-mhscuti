import requests
import time
import json
import copy
import os

def manhattan_distance(p1, p2):
    return abs(p1['x'] - p2['x']) + abs(p1['y'] - p2['y'])

def path_to_target(start, target):
    directions = []
    x, y = start['x'], start['y']
    tx, ty = target['x'], target['y']

    while x != tx:
        if x < tx:
            directions.append("EAST")
            x += 1
        else:
            directions.append("WEST")
            x -= 1

    while y != ty:
        if y < ty:
            directions.append("SOUTH")
            y += 1
        else:
            directions.append("NORTH")
            y -= 1

    return directions

def calculate_greedy_value(item, current_pos, inventory_count, inventory_size, has_red_button=False):
    distance = manhattan_distance(current_pos, item['position'])
    
    if item['type'] == 'DiamondGameObject':
        if inventory_count >= inventory_size - 1:
            return 1.0 / (distance + 5)
        else:
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

def main():
    os.makedirs("Randy", exist_ok=True)
    
    API_BASE_URL = "https://717a-182-253-63-43.ngrok-free.app/api"
    BOT_ID = "9f7b0386-0bbd-4438-b3a5-7c253f0f8f88"
    BASE_URL = f"{API_BASE_URL}/bots/{BOT_ID}"
    
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    
    bot_response = requests.get(f"{API_BASE_URL}/bots/{BOT_ID}", headers=headers)
    
    bot_info = {
        "id": BOT_ID,
        "name": "randyGG",
        "email": "randyhendriyawan@gmail.com"
    }
    
    try:
        bot_data = bot_response.json()
        bot_info = {
            "id": bot_data.get("id", BOT_ID),
            "name": bot_data.get("name", "randyGG"),
            "email": bot_data.get("email", "randyhendriyawan@gmail.com")
        }
    except Exception as e:
        pass
    
    boards_response = requests.get(f"{API_BASE_URL}/boards", headers=headers)
    board_id = 9
    
    try:
        boards_data = boards_response.json()
        if boards_data and len(boards_data) > 0:
            board_id = boards_data[0].get("id", 9)
    except Exception as e:
        pass
    
    with open("Randy/bot_log.txt", "a") as log_file:
        log_file.write(f"\n\n--- Bot Session Started at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
    
    join_payload = {
        "preferredBoardId": board_id,
        "name": bot_info['name']
    }
    
    response = requests.post(f"{BASE_URL}/join", json=join_payload, headers=headers)

    try:
        data = response.json()
        if "statusCode" in data and data["statusCode"] >= 400:
            return
    except Exception as e:
        return

    if not data or "gameObjects" not in data:
        return

    bot_obj = None
    base_obj = None
    inventory_size = 5
    inventory_count = 0
    
    for obj in data.get("gameObjects", []):
        if obj.get("type") == "BotGameObject":
            bot_obj = obj
            if "properties" in obj and "inventory" in obj["properties"]:
                inventory_count = len(obj["properties"]["inventory"])
            if "properties" in obj and "inventorySize" in obj["properties"]:
                inventory_size = obj["properties"]["inventorySize"]
        elif obj.get("type") == "BaseGameObject" and "properties" in obj:
            if obj["properties"].get("ownerId") == BOT_ID:
                base_obj = obj

    if bot_obj is None:
        return

    bot_pos = bot_obj["position"]
    current_pos = copy.deepcopy(bot_pos)
    
    last_positions = []
    stuck_counter = 0
    MAX_STUCK_COUNT = 3
    game_active = True

    while game_active:
        if last_positions and all(pos == current_pos for pos in last_positions[-3:]):
            stuck_counter += 1
            
            if stuck_counter >= MAX_STUCK_COUNT:
                if diamond_button:
                    best_target = diamond_button
                    best_target["type"] = "DiamondButtonGameObject"
                    target_pos = best_target["position"]
                    steps = path_to_target(current_pos, target_pos)
                    stuck_counter = 0
                    last_positions = []
                elif base_position and inventory_count > 0:
                    best_target = base_obj
                    best_target["type"] = "BaseGameObject"
                    target_pos = best_target["position"]
                    steps = path_to_target(current_pos, target_pos)
                    stuck_counter = 0
                    last_positions = []
        
        if len(last_positions) >= 5:
            last_positions.pop(0)
        last_positions.append(copy.deepcopy(current_pos))
        
        inventory_count = 0
        if "properties" in bot_obj and "inventory" in bot_obj["properties"]:
            inventory_items = bot_obj["properties"]["inventory"]
            inventory_count = len(inventory_items)
        
        diamonds = []
        teleporters = []
        diamond_button = None
        base_position = None
        
        total_diamonds = 0
        total_high_value_diamonds = 0
        
        for obj in data.get("gameObjects", []):
            obj_type = obj.get("type")
            
            if obj_type == "DiamondGameObject":
                total_diamonds += 1
                points = obj.get("properties", {}).get("points", 1)
                if points > 1:
                    total_high_value_diamonds += 1
            
            if obj_type == "DiamondGameObject":
                diamond_pos = obj["position"]
                points = obj.get("properties", {}).get("points", 1)
                
                diamond_info = {
                    "id": obj["id"],
                    "position": diamond_pos,
                    "points": points,
                    "distance": manhattan_distance(current_pos, diamond_pos),
                    "type": "DiamondGameObject",
                    "is_red": points > 1
                }
                
                if inventory_count < inventory_size:
                    diamonds.append(diamond_info)
                
            elif obj_type == "DiamondButtonGameObject":
                diamond_button = {
                    "id": obj["id"],
                    "position": obj["position"],
                    "distance": manhattan_distance(current_pos, obj["position"]),
                    "type": "DiamondButtonGameObject"
                }
            
            elif obj_type == "BaseGameObject" and "properties" in obj:
                if obj["properties"].get("ownerId") == BOT_ID:
                    base_position = obj["position"]
                    base_obj = {
                        "id": obj["id"],
                        "position": base_position,
                        "distance": manhattan_distance(current_pos, base_position),
                        "type": "BaseGameObject"
                    }
            
            elif obj_type == "TeleportGameObject":
                teleporter = {
                    "id": obj["id"],
                    "position": obj["position"],
                    "pairId": obj.get("properties", {}).get("pairId", ""),
                    "distance": manhattan_distance(current_pos, obj["position"]),
                    "type": "TeleportGameObject"
                }
                teleporters.append(teleporter)
        
        potential_targets = []
        
        if inventory_count >= inventory_size and base_position:
            base_obj["greedy_value"] = 100
            potential_targets.append(base_obj)
        else:
            if inventory_count < inventory_size:
                potential_targets.extend(diamonds)
            
            if base_position and inventory_count > 0:
                potential_targets.append(base_obj)
            
            if diamond_button and (total_diamonds < 10 or total_high_value_diamonds < 3):
                potential_targets.append(diamond_button)
            
            potential_targets.extend(teleporters)
            
            if not potential_targets and inventory_count > 0 and base_position:
                potential_targets.append(base_obj)
            
            if not potential_targets and diamond_button:
                potential_targets.append(diamond_button)

        if not (inventory_count >= inventory_size and base_position):
            for target in potential_targets:
                has_red_button = (diamond_button is not None)
                target["greedy_value"] = calculate_greedy_value(
                    target, current_pos, inventory_count, inventory_size, has_red_button
                )
        
        potential_targets.sort(key=lambda t: t["greedy_value"], reverse=True)
        
        if not potential_targets:
            game_active = False
            break
            
        best_target = potential_targets[0]
        target_type = best_target["type"]
        target_pos = best_target["position"]
        
        steps = path_to_target(current_pos, best_target["position"])
        
        move_url = f"{BASE_URL}/move"
        for direction in steps:
            move_payload = {"direction": direction}
            move_response = requests.post(move_url, json=move_payload, headers=headers)
            
            try:
                move_data = move_response.json()
                data = move_data

                if target_type == "DiamondGameObject" and best_target.get("is_red", False):
                    for obj in data.get("gameObjects", []):
                        if obj.get("type") == "BotGameObject":
                            bot_obj = obj
                            if "properties" in obj and "inventory" in obj["properties"]:
                                new_inv_count = len(obj["properties"]["inventory"])
                                inventory_count = new_inv_count
                                
                                if new_inv_count >= inventory_size:
                                    break
                            break
                
                for obj in data.get("gameObjects", []):
                    if obj.get("type") == "BotGameObject":
                        bot_obj = obj
                        break
                
                with open("Randy/bot_log.txt", "a") as log_file:
                    new_inventory_count = 0
                    if "properties" in bot_obj and "inventory" in bot_obj["properties"]:
                        new_inventory_count = len(bot_obj["properties"]["inventory"])
                    
                    log_file.write(f"{time.strftime('%H:%M:%S')} - Move {direction} - Inventory: {new_inventory_count}/{inventory_size}\n")
                
                if direction == "NORTH": current_pos["y"] -= 1
                elif direction == "SOUTH": current_pos["y"] += 1
                elif direction == "EAST": current_pos["x"] += 1
                elif direction == "WEST": current_pos["x"] -= 1
                
                if target_type == "TeleportGameObject" and manhattan_distance(current_pos, target_pos) == 0:
                    for obj in data.get("gameObjects", []):
                        if obj.get("type") == "BotGameObject":
                            current_pos = obj["position"]
                            break
                
                if "gameObjects" not in move_data:
                    game_active = False
                    break
            
            except Exception as e:
                game_active = False
                break
            
            time.sleep(0.2)

if __name__ == "__main__":
    main()