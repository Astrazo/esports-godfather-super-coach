# Setup mastery functions.  This does not live on the graph
def create_empty_masteries(G):
    return {
        hero: {
            position: 0
            for position in G.nodes[hero]["tiers"]
        }
        for hero in G.nodes
    }

def set_mastery(masteries, hero: str, position: str, level: int):
    if hero not in masteries:
        raise ValueError(f"Unknown hero: {hero}")

    if position not in masteries[hero]:
        raise ValueError(f"{hero} cannot play {position}")

    if not 0 <= level <= 7:
        raise ValueError("Mastery must be between 0 and 7")

    masteries[hero][position] = level


# Build hero tier and master lookups
tiers = defaultdict(dict)
t1_masteries = create_empty_masteries(G_master)
t2_masteries = create_empty_masteries(G_master)

# Build t1 masteries  - for every position that this hero can be in, what is the mastery of the actual players?
for _, row in hero_tier_list.iterrows():
    tiers[row["Name"]][row["Position"]] = row["tier_score"]

    set_mastery(t1_masteries, row["Name"], row["Position"], random.randint(0, 7))

print(t1_masteries["Frank"])
print(tiers["Frank"])

# Build t2 masteries
for _, row in hero_tier_list.iterrows():
    tiers[row["Name"]][row["Position"]] = row["tier_score"]
    set_mastery(t2_masteries, row["Name"], row["Position"], random.randint(0, 7))
print(t1_masteries["Frank"])
print(tiers["Frank"])
