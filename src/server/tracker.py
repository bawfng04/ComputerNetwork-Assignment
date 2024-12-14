import json
import re
import socket
import sys


def handle_client(client_socket):
    data = client_socket.recv(1024).decode()
    # if data == "":
    #     # print("do ngu do an hai")
    #     print("Client disconnected")
    #     return
    data = json.loads(data)

    if data["action"] == "upload":
        upload(data)
    elif data["action"] == "download":
        download(data)
    elif data["action"] == "downloaded":
        downloaded(data)
    elif data["action"] == "my_torrents":
        list_torrents(data)
    elif data["action"] == "connect":
        print(f"Node connect from {data['node_ip']}:{data['node_port']}")


def upload(data):
    del data["action"]
    for torrent in torrents:
        if torrent["info_hash"] == data["info_hash"]:
            message = {"status": "failed", "message": "Torrent already exists"}
            client_socket.sendall(json.dumps(message).encode())
            return

    torrents.append(data)
    message = {"status": "success", "message": "Torrent uploaded"}
    client_socket.sendall(json.dumps(message).encode())
    # print(torrents)
    new_data = {
        "ip": data["node_ip"],
        "port": data["node_port"],
        "info_hash": data["info_hash"],
    }
    peer_on_torrent.append(new_data)


def download(data):
    # response = {}
    info_hash = ""
    match = re.search(r"xt=urn:btih:([a-fA-F0-9]{40})", data["magnet_text"])
    if match:
        info_hash = match.group(1)
    else:
        message = {"status": "failed", "message": "Invalid magnet link"}
        client_socket.sendall(json.dumps(message).encode())
        return

    flag = False
    files = []
    for torrent in torrents:
        if torrent["info_hash"] == info_hash:
            files = torrent["files"]
            flag = True
            break

    if not flag:
        message = {"status": "failed", "message": "Torrent not found"}
        client_socket.sendall(json.dumps(message).encode())
        return

    peers = []
    for peer in peer_on_torrent:
        if peer["info_hash"] == info_hash:
            peers.append({"ip": peer["ip"], "port": peer["port"]})

    if not peers:
        message = {"status": "failed", "message": "No peers seeding this torrent"}
        client_socket.sendall(json.dumps(message).encode())
        return

    message = {"status": "success", "files": files, "peers": peers}
    client_socket.sendall(json.dumps(message).encode())


def downloaded(data):
    # pass
    info_hash = ""
    match = re.search(r"xt=urn:btih:([a-fA-F0-9]{40})", data["magnet_text"])
    if match:
        info_hash = match.group(1)
    else:
        message = {"status": "failed", "message": "Invalid magnet link"}
        client_socket.sendall(json.dumps(message).encode())
        return

    ip = data["node_ip"]
    port = data["node_port"]

    for peer in peer_on_torrent:
        if peer["info_hash"] == info_hash and peer["ip"] == ip and peer["port"] == port:
            # peer_on_torrent.remove(peer)
            # break
            return

    new_data = {
        "ip": data["node_ip"],
        "port": data["node_port"],
        "info_hash": info_hash,
    }

    peer_on_torrent.append(new_data)


def list_torrents(data):
    ip = data["node_ip"]
    port = data["node_port"]

    listTorrent = []
    for torrent in torrents:
        if torrent["node_ip"] == ip and torrent["node_port"] == port:
            num_seeding = 0
            for peer in peer_on_torrent:
                if peer["info_hash"] == torrent["info_hash"]:
                    num_seeding += 1

            magnet_text = f"magnet:?xt=urn:btih:{torrent['info_hash']}&dn={torrent['torrent_name']}&tr={TRACKER_IP}:{TRACKER_PORT}"

            temp = {
                "torrent_name": torrent["torrent_name"],
                "magnet_text": magnet_text,
                "num_seeding": num_seeding,
            }
            listTorrent.append(temp)

    if not listTorrent:
        message = {"status": "failed", "message": "No torrent found"}
        client_socket.sendall(json.dumps(message).encode())
        return
    message = {"status": "success", "torrents": listTorrent}
    client_socket.sendall(json.dumps(message).encode())


if len(sys.argv) != 3:
    print("Usage: python tracker.py <tracker_ip> <tracker_port>")
    sys.exit(1)

TRACKER_IP = sys.argv[1]
TRACKER_PORT = int(sys.argv[2])

try:
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((TRACKER_IP, TRACKER_PORT))
    server_socket.listen()
    server_socket.settimeout(1)
    print("Tracker server is running...")
except Exception:
    print("Error: Tracker ip or port is invalid")
    sys.exit(1)

running = True
torrents = []
peer_on_torrent = []


try:
    while running:
        try:
            client_socket, addr = server_socket.accept()
            handle_client(client_socket)
            client_socket.close()
        except socket.timeout:
            pass


except KeyboardInterrupt:
    print("Tracker server is closing...")
    running = False
    server_socket.close()
