# Global Helper Functions
def get_hero_best_positions(hero_name: str | list[str], tier=1, verbose=False) -> dict[str, list[dict]]:
    output = {}

    names = [hero_name] if isinstance(hero_name, str) else hero_name.copy()

    for name in names:
        hero_rows = hero_tier_list[hero_tier_list["Name"] == name]
        max_score = hero_rows["tier_score"].max()
        target_score = max_score - (tier - 1)

        best_positions = hero_rows.loc[
            hero_rows["tier_score"] == target_score,
            ["Position", "Tier"]
        ].to_dict("records")

        if not best_positions:
            print(f"No heroes found under the name {name}.")
            continue

        position_names = [position["Position"] for position in best_positions]
        print_out = f"{name}'s best position is {', '.join(position_names)}."

        if verbose:
            print(print_out)

        output[name] = best_positions

    return output

# Get the best heroes for a position
def get_position_best_heroes(position: str | list[str], tier=1, verbose=False) -> dict[str, list[dict]]:
    output = {}

    positions = [position] if isinstance(position, str) else position.copy()

    for position in positions:
        position_rows = hero_tier_list[hero_tier_list["Position"] == position]
        max_score = position_rows["tier_score"].max()
        target_score = max_score - (tier - 1)

        best_heroes = position_rows.loc[
            position_rows["tier_score"] == target_score,
            ["Name", "Tier"]
        ].to_dict("records")

        if not best_heroes:
            print(f"No heroes found for the {position} position.")
            continue

        hero_names = [hero["Name"] for hero in best_heroes]
        print_out = f"Best heroes for the {position.lower()} position are {', '.join(hero_names)}."

        if verbose:
            print(print_out)

        output[position] = best_heroes

    return output

#best_positions = get_hero_best_positions("Bart", verbose=True, tier=1)
#best_heroes = get_position_best_heroes(["Top", "Mid"], verbose=True)


