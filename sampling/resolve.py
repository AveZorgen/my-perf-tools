import subprocess

def parse_maps(maps_lines):
    mappings = {}
    for line in maps_lines:
        parts = line.split()
        if len(parts) < 6:
            continue
        address_range = parts[0]
        # permissions = parts[1]
        offset = parts[2]
        # device = parts[3]
        # inode = parts[4]
        pathname = ' '.join(parts[5:])
        start, end = address_range.split('-')
        mappings[pathname] = {
            'start': int(start, 16),
            'end': int(end, 16),
            'offset': int(offset, 16),
            'addresses': set()
        }
    return mappings


def main():
    with open('mpt.map', 'r') as file:
        lines = file.readlines()

    maps_lines = [line.strip() for line in lines if 'r-xp' in line and '/' in line]
    mappings = parse_maps(maps_lines)


    with open('mpt.txt', 'r') as file:
        lines = file.readlines()
    
    address_lines = [line.strip() for line in lines]

    for line in address_lines:
        parts = line.strip().split()
        if len(parts) < 3:
            continue

        address = int(parts[0], 16)
        for mapping in mappings.values():
            if mapping['start'] <= address <= mapping['end']:
                mapping['addresses'].add(address)
                break
    
    text = '\n'.join(address_lines)

    for pathname, mapping in mappings.items():
        if not mapping['addresses']:
            continue

        start, offset = mapping['start'], mapping['offset']
        address_orig = list(mapping['addresses'])
        addresses = map(lambda address: hex(address - start + offset), address_orig)

        try:
            result = subprocess.check_output(['addr2line', '-e', pathname, '-f', '-C', *addresses], stderr=subprocess.STDOUT)
            data = result.decode('utf-8').strip().splitlines()
            for i in range(len(data) // 2):
                text = text.replace(hex(address_orig[i]), data[i * 2])
        except subprocess.CalledProcessError:
            continue

    print(text)


if __name__ == "__main__":
    main()
