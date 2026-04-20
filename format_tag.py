from time import sleep
from smartcard.System import readers

BLOCK_SIZE = 4
LAST_WRITABLE_BLOCK = 78


def pick_reader():
    all_readers = readers()
    if not all_readers:
        raise Exception("No reader was found")

    for r in all_readers:
        if "(1)" in str(r):
            return r

    return all_readers[0]


def connect_to_tag(reader, timeout_seconds=60):
    print("Using reader:", reader)
    print("Waiting for tag...")

    last_error = None

    for _ in range(timeout_seconds * 2):
        try:
            connection = reader.createConnection()
            connection.connect()
            print("Tag detected!")
            return connection
        except Exception as e:
            last_error = e
            sleep(0.5)

    raise Exception(f"No tag was found: {last_error}")


def get_uid(connection):
    cmd = [0xFF, 0xCA, 0x00, 0x00, 0x00]
    data, sw1, sw2 = connection.transmit(cmd)

    if (sw1, sw2) != (0x90, 0x00):
        raise Exception(f"Could not reada UID: {sw1:02X} {sw2:02X}")

    print("UID:", " ".join(f"{b:02X}" for b in data))


def write_block(connection, block, data):
    data = list(data)

    while len(data) < BLOCK_SIZE:
        data.append(0x00)

    cmd = [0xFF, 0xFB, 0x00, 0x00, 0x06, 0x21, block] + data
    resp, sw1, sw2 = connection.transmit(cmd)

    print(f"WRITE block {block}: {sw1:02X} {sw2:02X}")

    if (sw1, sw2) != (0x90, 0x00):
        raise Exception(f"Write failed block {block}: {sw1:02X} {sw2:02X}")


def main():
    reader = pick_reader()
    connection = connect_to_tag(reader)
    get_uid(connection)

    zero_block = [0x00, 0x00, 0x00, 0x00]

    print(f"Formatting blocks 0..{LAST_WRITABLE_BLOCK}...")
    for block in range(0, LAST_WRITABLE_BLOCK + 1):
        write_block(connection, block, zero_block)

    print("Format complete!")


if __name__ == "__main__":
    main()
