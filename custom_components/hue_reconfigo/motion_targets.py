"""Resolve exposed HA groups and Hue rooms/zones to controllable leaf entities."""


def hue_group_members(devices, groups, entities):
    """Match Hue resource identifiers; never guess group membership from names."""
    by_id = {item["id"]: item for item in [*devices, *groups]}

    def lights(rid, seen=None):
        seen = set(seen or ())
        if rid in seen:
            return set()
        seen.add(rid)
        item = by_id.get(rid, {})
        found = {s["rid"] for s in item.get("services", []) if s["rtype"] == "light"}
        for child in item.get("children", []):
            if child["rtype"] == "light":
                found.add(child["rid"])
            else:
                found.update(lights(child["rid"], seen))
        return found

    result = {}
    for group in groups:
        leaf = {entities[rid] for rid in lights(group["id"]) if rid in entities}
        if not leaf:
            continue
        for service in group.get("services", []):
            if service["rtype"] == "grouped_light" and service["rid"] in entities:
                result[entities[service["rid"]]] = leaf
    return result


def expand_targets(hass, selected, hue_groups):
    def expand(entity, seen=None):
        seen = set(seen or ())
        if entity in seen:
            return set()
        seen.add(entity)
        state = hass.states.get(entity)
        children = hue_groups.get(entity) or (state.attributes.get("entity_id") if state else None)
        if isinstance(children, str):
            children = [children]
        if not isinstance(children, (list, tuple, set)) or not children:
            return {entity}
        result = set()
        for child in children:
            if isinstance(child, str) and child.startswith("light."):
                result.update(expand(child, seen))
        return result

    return set().union(*(expand(e) for e in selected)) if selected else set()
