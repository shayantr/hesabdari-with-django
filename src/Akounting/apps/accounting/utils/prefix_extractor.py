def extract_all_prefixes(post_data, file_data):
    prefixes = set()
    combined_keys = list(post_data.keys()) + list(file_data.keys())

    for key in combined_keys:
        if '-new' in key:
            prefix = key.split('-')[0]
            prefixes.add(prefix)
    return prefixes

def extract_all_update_prefixes(post_data, file_data):
    prefixes = set()
    combined_keys = list(post_data.keys()) + list(file_data.keys())

    for key in combined_keys:
        if '-update' in key:
            prefix = key.split('-')[0]
            prefixes.add(prefix)
    return prefixes