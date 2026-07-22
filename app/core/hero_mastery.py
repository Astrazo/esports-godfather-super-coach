POSITIONS = ["Top", "Jungler", "Mid", "Bot", "Support"]

# Setup mastery functions.  This does not live on the graph
def create_empty_masteries(G) -> dict[str, dict[str: int]]:
    return {hero: {position: 0 for position in G.nodes[hero]["tiers"]} for hero in G.nodes} # mastery can only exist where a tier exists

# A function to create a structure to house enemy signiture heroes to help with the draft
def create_empty_signitures() -> dict[str, set]: # position -> heroes
    return {position: set() for position in POSITIONS}

# Set the masterty of a hero
def set_mastery(masteries: dict[str, dict[str: int]], hero: str, position: str, level: int):
    if hero not in masteries:
        raise ValueError(f"Unknown hero: {hero}")

    if position not in masteries[hero]:
        raise ValueError(f"{hero} cannot play {position}")

    if not 0 <= level <= 7:
        raise ValueError("Mastery must be between 0 and 7")

    masteries[hero][position] = level

def increase_mastery(masteries: dict[str, dict[str: int]], hero: str, position: str):
    if hero not in masteries:
        raise ValueError(f"Unknown hero: {hero}")

    if position not in masteries[hero]:
        raise ValueError(f"{hero} cannot play {position}")
    
    curr_level = masteries[hero][position]
    if curr_level >= 7:
        raise ValueError("Mastery already at max!")
    
    masteries[hero][position] += 1

def decrease_mastery(masteries: dict[str, dict[str: int]], hero: str, position: str):
    if hero not in masteries:
        raise ValueError(f"Unknown hero: {hero}")

    if position not in masteries[hero]:
        raise ValueError(f"{hero} cannot play {position}")
    
    curr_level = masteries[hero][position]
    if curr_level <= 0:
        raise ValueError("Mastery already at min!")
    
    masteries[hero][position] -= 1