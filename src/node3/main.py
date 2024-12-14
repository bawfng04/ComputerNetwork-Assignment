import hashlib
import json
import os
import queue
import random
import socket
import threading
import time
from tqdm import tqdm  # Add this import

TRACKER_IP = "127.0.0.1"
TRACKER_PORT = 5000

NODE_IP = "127.0.0.1"
NODE_PORT = 11113

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
                while True:
                    data = f.read(buffer_size)
                    if not data:
                        break
                    sha1.update(data)
        info_hash = sha1.hexdigest()
        return info_hash
    except FileNotFoundError:
        print(f"File '{file}' not found.")
        return None

def upload_torrent(files, torrent_name):
    info_hash = get_info_hash(files.copy())
    if info_hash is None:
        return
    magnet_text = f"magnet:?xt=urn:btih:{info_hash}&dn={torrent_name}&tr={TRACKER_IP}:{TRACKER_PORT}"

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
            print("Torrent already exists")

def dowload_torrent(magnet_text):
    data = {"action": "download", "magnet_text": magnet_text}

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((TRACKER_IP, TRACKER_PORT))
    client.sendall(json.dumps(data).encode())
    response = json.loads(client.recv(1024).decode())

    if response["status"] == "failed":
        print("Download failed")
        print(response["message"])
        return

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
        q = queue.Queue()
        for i in range(chunk_number):
            q.put(i)

        progress_bar = tqdm(range(int(9e6)))
        start_time = time.time()

        def start_download():
            while not q.empty():
                chunk_index = q.get()
                peer = random.choice(peers)
                data_chunk = download_chunk(peer, chunk_index)
                if data_chunk:
                    f.seek(chunk_index * CHUNK_SIZE)
                    f.write(data_chunk)
                    progress_bar.update(len(data_chunk))
                else:
                    q.put(chunk_index)
                q.task_done()

        def download_chunk(peer, chunk_index):
            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((peer["ip"], peer["port"]))
                request = {"file_path": os.path.join(FILES_DIR, file_name), "chunk_index": chunk_index}
                client_socket.sendall(json.dumps(request).encode())
                data_chunk = client_socket.recv(CHUNK_SIZE)
                client_socket.close()
                return data_chunk
            except Exception:
                return None

        threads = []
        for _ in range(4):
            thread = threading.Thread(target=start_download)
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        end_time = time.time()
        speed = file_size / (end_time - start_time)
        progress_bar.close()
        f.close()
        print(f"Downloaded file {file_name} at {speed / 1024:.2f} KB/s")

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
        for torrent in response["torrents"]:
            print(f"Torrent Name: {torrent['torrent_name']}")
            print(f"Magnet Link: {torrent['magnet_text']}")
            print(f"Number of Seeders: {torrent['num_seeding']}")
            print("-----------------------------")

def start_node_server():
    node_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    node_server.bind((NODE_IP, NODE_PORT))
    node_server.listen()

    while True:
        client_socket, addr = node_server.accept()
        handle_client(client_socket, addr)
        client_socket.close()

def handle_client(client_socket, addr):
    data = json.loads(client_socket.recv(1024).decode())
    file_path = data["file_path"]
    chunk_index = data["chunk_index"]

    if not os.path.exists(file_path):
        print(f"File {file_path} not found")
        return
    f = open(file_path, "rb")
    f.seek(chunk_index * CHUNK_SIZE)
    data_chunk = f.read(CHUNK_SIZE)
    client_socket.sendall(data_chunk)
    f.close()

def process_input():
    command = input("$ ")
    params = command.split(" ")
    if params[0] == "upload":
        files = []
        name = ""
        for i in range(1, len(params)):
            if params[i] == "-n" and i + 1 < len(params):
                name = params[i + 1]
                break
            else:
                files.append(params[i])
        if len(files) == 0:
            print("No files specified")
            return
        if name == "":
            print("No torrent name specified, use -n <torrent_name>")
            return

        upload_torrent(files, name)
    elif params[0] == "download":
        if len(params) < 2:
            print("Please provide a magnet link")
            return
        magnet_text = params[1]
        dowload_torrent(magnet_text)
    elif params[0] == "exit":
        exit()
    elif params[0] == "fetch":
        fetch_torrents()
    elif params[0] == "help":
        print("upload <file1> <file2> ... -n <torrent_name>")
        print("download <magnet_link>")
        print("fetch")
        print("exit")
    elif params[0] == "cls":
        os.system("cls")
    else:
        print("Invalid command")

if __name__ == "__main__":
    if not os.path.exists(FILES_DIR):
        os.makedirs(FILES_DIR)

    threading.Thread(target=start_node_server).start()

    while True:
        process_input()