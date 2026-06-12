from collections import defaultdict

def validate_data(hero_tier_list, hero_relationships):
    heroes_t = set(hero_tier_list["Name"].unique().tolist())
    all_hero_names = set(all_hero_names)

    mismatches = []
    for hero in heroes_t:
        if hero in all_hero_names:
            continue
        mismatches.append((hero))

    if (len(heroes_t) != len(all_hero_names)) or mismatches:
        print("Names do not match.")
    else:
        print("Names match.")


# Build tag -> hero lookup so we can pump in heros if we see tags for synergies etc.
def tag_hero_map():
    lookup = defaultdict(list)
    for hero in all_hero_names:
        hero_data = relationships[relationships["name"] == hero]
        hero_tags = hero_data["tags"].tolist()[0].split(",")
        for tag in hero_tags:
            lookup[tag].append(hero)
    print(lookup)