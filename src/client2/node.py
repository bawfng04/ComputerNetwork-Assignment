import hashlib
import json
import os
import queue
import socket
import sys
import threading

import tqdm

FILES_DIR = ".\\files"
CHUNK_SIZE = 512 * 1024


def get_info_hash(files):
    files.sort()
    for i in range(len(files)):
        files[i] = os.path.join(FILES_DIR, files[i])
    sha1 = hashlib.sha1()
    buffer_size = CHUNK_SIZE

    try:
        for file in files:
            with open(file, "rb") as f:
                while chunk := f.read(buffer_size):
                    sha1.update(chunk)

        info_hash = sha1.hexdigest()
        return info_hash
    except FileNotFoundError:
        print(f"File '{file}' not found.")
        return None


def upload_torrent(files, torrent_name):

    info_hash = get_info_hash(files.copy())
    # print(info_hash)
    if info_hash is None:
        # print("Info hash is None")
        return
    magnet_text = f"magnet:?xt=urn:btih:{info_hash}&dn={torrent_name}&tr={TRACKER_IP}:{TRACKER_PORT}"

    # print(f"Magnet link: {magnet_text}")

    files_info = []
    for file in files:
        file_info = {
            "name": file,
            "size": os.path.getsize(os.path.join(FILES_DIR, file)),
        }
        files_info.append(file_info)

    data = {
        "action": "upload",
        "torrent_name": torrent_name,
        "info_hash": info_hash,
        "node_ip": NODE_IP,
        "node_port": NODE_PORT,
        "files": files_info,
    }

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.connect((TRACKER_IP, TRACKER_PORT))
        client.sendall(json.dumps(data).encode())
        response = json.loads(client.recv(1024).decode())
        if response["status"] == "success":
            print("Upload success")
            print(f"Torrent name: {torrent_name}")
            print(f"Magnet link: {magnet_text}")
        else:
            print("Upload failed")
            print("Torrennt already exists")


def dowload_torrent(magnet_text):
    # // Gửi yêu cầu tải file lên tracker
    data = {"action": "download", "magnet_text": magnet_text}

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((TRACKER_IP, TRACKER_PORT))
    client.sendall(json.dumps(data).encode())
    response = json.loads(client.recv(1024).decode())

    if response["status"] == "failed":
        print("Download failed")
        print(response["message"])
        return

    """response = {'status': 'success', 'files': [{'name': 'file1.txt', 'size': 11}], 'peers': [{'ip': '127.0.0.1', 'port': 6000}]}"""

    files = response["files"]
    peers = response["peers"]
    chunk_size = CHUNK_SIZE

    def download_file(file):
        file_name = file["name"]
        file_size = file["size"]
        file_path = os.path.join(FILES_DIR, file_name)
        chunk_number = file_size // CHUNK_SIZE + 1

        if os.path.exists(file_path):
            print(f"File {file_name} already exists")
            return

        f = open(file_path, "wb")
        bar = tqdm.tqdm(
            total=file_size,
            desc=f"Downloading {file_name}",
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
        )
        q = queue.Queue()
        for i in range(chunk_number):
            q.put(i)

        def start_download():
            while not q.empty():
                chunk_index = q.get()
                # print("Downloading chunk", chunk_index)
                download_chunk(peers[chunk_index % len(peers)], chunk_index)

        def download_chunk(peer, chunk_index):
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((peer["ip"], peer["port"]))

            message = {"file_path": file_path, "chunk_index": chunk_index}
            client_socket.sendall(json.dumps(message).encode())

            data = client_socket.recv(chunk_size)
            while True:
                new_data = client_socket.recv(chunk_size)
                if not new_data:
                    break
                data += new_data
            # n = len(data)
            # while n < chunk_size:
            #     data = data + client_socket.recv(chunk_size - n)
            #     n = len(data)
            f.seek(chunk_index * chunk_size)
            f.write(data)
            bar.update(len(data))

            client_socket.close()

        threads = []
        for _ in range(4):
            thread = threading.Thread(target=start_download)
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        f.close()
        bar.close()
        print(f"Downloaded file {file_name}")

    for file in files:
        download_file(file)

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((TRACKER_IP, TRACKER_PORT))
    data = {
        "action": "downloaded",
        "magnet_text": magnet_text,
        "node_ip": NODE_IP,
        "node_port": NODE_PORT,
    }
    client.sendall(json.dumps(data).encode())
    print("Download torrent success")


def fetch_torrents():
    data = {"action": "my_torrents", "node_ip": NODE_IP, "node_port": NODE_PORT}
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((TRACKER_IP, TRACKER_PORT))
    client.sendall(json.dumps(data).encode())
    response = json.loads(client.recv(4 * 1024).decode())

    if response["status"] == "failed":
        print("Fetch failed")
        print(response["message"])
    else:
        print("Fetch success")
        # print(response["torrents"])
        for torrent in response["torrents"]:
            print(torrent)


def start_node_server():
    try:
        node_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        node_server.bind((NODE_IP, NODE_PORT))
        node_server.listen()
        node_server.settimeout(1)

        # print(f"Node server started at {NODE_IP}:{NODE_PORT}")

        while running:
            try:
                client_socket, addr = node_server.accept()
                handle_client(client_socket, addr)
                client_socket.close()
            except socket.timeout:
                pass
        node_server.close()
    except Exception:
        print("Error: Node ip or port is invalid")


def handle_client(client_socket, addr):
    # response = {"file_path": file_path, "chunk_index": chunk_index}
    data = json.loads(client_socket.recv(1024).decode())
    file_path = data["file_path"]
    chunk_index = data["chunk_index"]

    if not os.path.exists(file_path):
        print(f"File {file_path} not found")
        return
    f = open(file_path, "rb")
    f.seek(chunk_index * CHUNK_SIZE)
    data = f.read(CHUNK_SIZE)
    client_socket.sendall(data)
    f.close()


def process_input():
    global running
    command = input("$ ")
    params = command.split(" ")
    if params[0] == "upload":
        # upload file1 file2 file3 -n torrent_name
        # files = params[1].split(",")
        # name = params[2]

        files = []
        name = ""
        for i in range(1, len(params)):
            if params[i] == "-n":
                name = params[i + 1]
                break
            files.append(params[i])
        if len(files) == 0:
            print("No files to upload")
            return

        if name == "":
            name = files[0]
            for i in range(1, len(files)):
                name += "_" + files[i]

        upload_torrent(files, name)
    elif params[0] == "download":
        if len(params) < 2:
            print("Invalid command")
            return
        magnet_text = params[1]
        dowload_torrent(magnet_text)
    elif params[0] == "exit":
        running = False
    elif params[0] == "fetch":
        fetch_torrents()
    elif params[0] == "help":
        print("upload file1 file2 file3 -n torrent_name")
        print("download magnet_link")
        print("fetch")
        print("exit")
    elif params[0] == "cls":
        os.system("cls")
    else:
        print("Invalid command")


running = True

if __name__ == "__main__":

    if len(sys.argv) != 5:
        print("Usage: python node.py <tracker_ip> <tracker_port> <node_ip> <node_port>")
        sys.exit(1)

    TRACKER_IP = sys.argv[1]
    TRACKER_PORT = int(sys.argv[2])
    NODE_IP = sys.argv[3]
    NODE_PORT = int(sys.argv[4])

    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((TRACKER_IP, TRACKER_PORT))

        message = {"action": "connect", "node_ip": NODE_IP, "node_port": NODE_PORT}
        client.sendall(json.dumps(message).encode())
        print(f"Connected to tracker server at {TRACKER_IP}:{TRACKER_PORT}")
        client.close()
    except Exception:
        print("Error: Tracker ip or port is invalid")
        sys.exit(1)

    if not os.path.exists(FILES_DIR):
        os.makedirs(FILES_DIR)

    threading.Thread(target=start_node_server).start()

    while running:
        process_input()
