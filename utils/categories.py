def build_tree(categories : list ) -> dict:
    tree = {}
    nodes = {}

    # Crea nodi base senza figli
    for cat in categories:
        cat['children'] = []
        nodes[cat['id']] = cat

    # Assegna i figli
    for cat in categories:
        parent_id = cat['parent']
        if parent_id == '#':
            tree[cat['id']] = cat
        else:
            if parent_id in nodes:
                nodes[parent_id]['children'].append(cat)

    return tree