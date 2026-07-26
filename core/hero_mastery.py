POSITIONS = ["Top", "Jungler", "Mid", "Bot", "Support"]

def create_default_masteries(G) -> dict[str, dict[str: int]]:
    """For each node in the graph, set each playable position to 0 mastery.

    Returns:
        _type_: _description_
    """
    return {hero: {position: 0 for position in G.nodes[hero]["tiers"]} for hero in G.nodes} # mastery can only exist where a tier exists

def set_mastery(masteries: dict[str, dict[str: int]], hero: str, position: str, level: int):
    """Set the mastery of a hero.

    Args:
        masteries (_type_): _description_
        hero (str): _description_
        position (str): _description_
        level (int): _description_

    Raises:
        ValueError: _description_
        ValueError: _description_
        ValueError: _description_
    """
    if hero not in masteries:
        raise ValueError(f"Unknown hero: {hero}")

    if position not in masteries[hero]:
        raise ValueError(f"{hero} cannot play {position}")

    if not 0 <= level <= 7:
        raise ValueError("Mastery must be between 0 and 7")

    masteries[hero][position] = level

def increase_mastery(masteries: dict[str, dict[str: int]], hero: str, position: str):
    """Function to increase the mastery of a hero by 1.

    Args:
        masteries (_type_): _description_
        hero (str): _description_
        position (str): _description_

    Raises:
        ValueError: _description_
        ValueError: _description_
        ValueError: _description_
    """
    if hero not in masteries:
        raise ValueError(f"Unknown hero: {hero}")

    if position not in masteries[hero]:
        raise ValueError(f"{hero} cannot play {position}")
    
    curr_level = masteries[hero][position]
    if curr_level >= 7:
        raise ValueError("Mastery already at max!")
    
    masteries[hero][position] += 1

def decrease_mastery(masteries: dict[str, dict[str: int]], hero: str, position: str):
    """Function to decrease the mastery of a hero by 1.

    Args:
        masteries (_type_): _description_
        hero (str): _description_
        position (str): _description_

    Raises:
        ValueError: _description_
        ValueError: _description_
        ValueError: _description_
    """
    if hero not in masteries:
        raise ValueError(f"Unknown hero: {hero}")

    if position not in masteries[hero]:
        raise ValueError(f"{hero} cannot play {position}")
    
    curr_level = masteries[hero][position]
    if curr_level <= 0:
        raise ValueError("Mastery already at min!")
    
    masteries[hero][position] -= 1