from time import sleep
import argparse
import os
from smartcard.System import readers

BLOCK_SIZE = 4
START_BLOCK = 0


# =========================
# Argument
# =========================
parser = argparse.ArgumentParser(description="Write BIN to NFC tag (SLIX2)")
parser.add_argument("-f", "--file", required=True, help="Path to .bin file")

args = parser.parse_args()
BIN_FILE = args.file

if not os.path.exists(BIN_FILE):
    raise Exception(f"Filen finns inte: {BIN_FILE}")


# =========================
# Reader
# =========================
def pick_reader():
    all_readers = readers()
    if not all_readers:
        raise Exception("Ingen reader hittades")

    for r in all_readers:
        if "(1)" in str(r):
            return r

    return all_readers[0]


# =========================
# Connect
# =========================
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

    raise Exception(f"Ingen tagg hittades: {last_error}")


# =========================
# UID
# =========================
def get_uid(connection):
    cmd = [0xFF, 0xCA, 0x00, 0x00, 0x00]
    data, sw1, sw2 = connection.transmit(cmd)

    if (sw1, sw2) != (0x90, 0x00):
        raise Exception(f"Kunde inte läsa UID: {sw1:02X} {sw2:02X}")

    print("UID:", " ".join(f"{b:02X}" for b in data))
    return data


# =========================
# Read
# =========================
def read_block(connection, block):
    cmd = [0xFF, 0xFB, 0x00, 0x00, 0x02, 0x20, block]
    resp, sw1, sw2 = connection.transmit(cmd)

    if (sw1, sw2) != (0x90, 0x00):
        raise Exception(f"Read failed block {block}: {sw1:02X} {sw2:02X}")

    return list(resp)


# =========================
# Write
# =========================
def write_block(connection, block, data):
    data = list(data)

    while len(data) < BLOCK_SIZE:
        data.append(0x00)

    cmd = [0xFF, 0xFB, 0x00, 0x00, 0x06, 0x21, block] + data
    resp, sw1, sw2 = connection.transmit(cmd)

    print(f"WRITE block {block}: {sw1:02X} {sw2:02X}")

    if (sw1, sw2) != (0x90, 0x00):
        raise Exception(f"Write failed block {block}: {sw1:02X} {sw2:02X}")


# =========================
# Main
# =========================
def main():
    reader = pick_reader()
    connection = connect_to_tag(reader)

    with open(BIN_FILE, "rb") as f:
        bin_data = list(f.read())

    print(f"File: {BIN_FILE}")
    print(f"BIN size: {len(bin_data)} bytes")

    get_uid(connection)

    total_blocks = (len(bin_data) + BLOCK_SIZE - 1) // BLOCK_SIZE
    last_block = START_BLOCK + total_blocks - 1

    print(f"Will write blocks {START_BLOCK}..{last_block}")

    if last_block > 78:
        raise Exception("Filen är för stor för SLIX2")

    # WRITE
    print("Writing...")
    for i in range(total_blocks):
        block = START_BLOCK + i
        chunk = bin_data[i * BLOCK_SIZE:(i + 1) * BLOCK_SIZE]
        write_block(connection, block, chunk)

    print("Write complete")

    # VERIFY
    print("Verifying...")
    read_back = []

    for i in range(total_blocks):
        block = START_BLOCK + i
        data = read_block(connection, block)
        read_back.extend(data[:BLOCK_SIZE])

    read_back = read_back[:len(bin_data)]

    if read_back == bin_data:
        print("✅ Verification OK")
    else:
        print("❌ Verification FAILED")


if __name__ == "__main__":
    main()
