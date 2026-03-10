import random
from game_engine import Game, UI

game = Game(25, 18, "Student Custom Game")
ui = UI()

# -----------------------------
# STUDENT CONFIG AREA
# -----------------------------
player_type = "knight"
start_x, start_y = 2, 2
background_index = 1
use_maze_border = 1

enemy_count = 5
gem_count = 4
collect_goal = 3
defeat_goal = 2
survive_goal_seconds = 20

# -----------------------------
# WORLD SETUP
# -----------------------------
game.spawnMaze(background_index, use_maze_border)

player = game.spawnPlayerXY(player_type, start_x, start_y)
player.maxSpeed = 6
player.maxHealth = 150
player.health = player.maxHealth
player.attackDamage = 50

game.addCollectGoal(collect_goal)
game.addDefeatGoal(defeat_goal)
game.addSurviveGoal(survive_goal_seconds)

game.addCustomGoal(
    "Collect 3 and defeat 2",
    lambda g: g.stats["collected"] >= 3 and g.stats["defeated"] >= 2
)

# -----------------------------
# FUNCTION + WHILE LOOP + RANDOM
# -----------------------------
def spawn_many_random(kind, amount):
    made = 0
    while made < amount:
        x = random.randint(1, 23)
        y = random.randint(1, 16)

        if abs(x - start_x) > 2 or abs(y - start_y) > 2:
            game.spawnXY(kind, x, y)
            made += 1

spawn_many_random("munchkin", enemy_count)
spawn_many_random("gold_coin", gem_count)

game.spawnXY("potion-medium", 10, 8)
game.spawnXY("lightstone", 18, 12)
game.spawnXY("skeleton", 15, 10)

ui.track(game, "defeated")
ui.track(game, "collected")
ui.track(game, "wins")
ui.track(game, "losses")

game.run()