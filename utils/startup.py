import os

def load_cogs(disallowed: set):
    file_list = []
    for root, _, files in os.walk('extensions/commands'):
        for filename in files:
            if not filename.endswith('.py'):
                continue
            path = f"{root}.{filename.replace('.py', '')}".replace("/", '.')
            if path.split('.')[-1] in disallowed:
                continue
            file_list.append(path)
    return file_list