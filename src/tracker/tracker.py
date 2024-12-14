import json
import re
import socket
from tqdm import tqdm
import time

TRACKER_IP = "127.0.0.1"
TRACKER_PORT = 5000


server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((TRACKER_IP, TRACKER_PORT))
server_socket.listen()

torrents = []
peer_on_torrent = []

#Chức năng chính: Quản lý thông tin về các torrents và các peers trong mạng peer-to-peer.
#Tracker đóng vai trò như một trung tâm điều phối, giúp các nodes tìm thấy nhau để chia sẻ
#các tệp tin.
def handle_client(client_socket):
    data = client_socket.recv(1024).decode()
    data = json.loads(data)

    if data["action"] == "upload": #để thông báo cho tracker rằng node muốn tải lên một torrent
        upload(data)
    elif data["action"] == "download": #để thông báo cho tracker rằng node muốn tải một torrent
        download(data)
    elif data["action"] == "downloaded": #để thông báo cho tracker rằng node đã tải xong một torrent
        downloaded(data)
    elif data["action"] == "my_torrents": #để lấy danh sách các torrents mà node đã tải lên
        list_torrents(data)


def upload(data):
    del data["action"] #Xóa trường action ra khỏi dữ liệu
    for torrent in torrents:
        if torrent["info_hash"] == data["info_hash"]: #Kiểm tra xem torrent đã tồn tại chưa
            message = {"status": "failed", "message": "Torrent already exists"}
            client_socket.sendall(json.dumps(message).encode())
            return

    torrents.append(data) #Thêm torrent vào danh sách torrents
    message = {"status": "success", "message": "Torrent uploaded"}
    client_socket.sendall(json.dumps(message).encode())
    # print(torrents)
    new_data = { #Thêm thông tin của peer vào danh sách peer_on_torrent
        "ip": data["node_ip"],
        "port": data["node_port"],
        "info_hash": data["info_hash"],
    }
    peer_on_torrent.append(new_data)


def download(data):
    # response = {}
    info_hash = ""
    # tìm kiếm thông tin hash từ magnet link
    match = re.search(r"xt=urn:btih:([a-fA-F0-9]{40})", data["magnet_text"])
    if match:
        info_hash = match.group(1) #Lấy giá trị băm từ magnet link
    else:
        message = {"status": "failed", "message": "Invalid magnet link"}
        client_socket.sendall(json.dumps(message).encode())
        return

    flag = False
    files = []
    #lặp qua danh sách torrents để tìm thông tin về torrent
    for torrent in torrents:
        if torrent["info_hash"] == info_hash:  #nếu tìm thấy thông tin về torrent
            files = torrent["files"]  #Lấy danh sách các file trong torrent
            flag = True
            break

    if not flag: #Nếu không tìm thấy thông tin về torrent
        message = {"status": "failed", "message": "Torrent not found"}
        client_socket.sendall(json.dumps(message).encode())
        return

    peers = []
    for peer in peer_on_torrent: #Lặp qua danh sách peer_on_torrent để tìm peer seeding torrent
        if peer["info_hash"] == info_hash: #Nếu tìm thấy peer seeding torrent
            peers.append({"ip": peer["ip"], "port": peer["port"]}) #Thêm thông tin peer vào danh sách peers

    if not peers: #Nếu không tìm thấy peer seeding torrent
        message = {"status": "failed", "message": "No peers seeding this torrent"} #Trả về thông báo lỗi
        client_socket.sendall(json.dumps(message).encode())
        return

    message = {"status": "success", "files": files, "peers": peers}
    client_socket.sendall(json.dumps(message).encode())


def downloaded(data): #Hàm thông báo cho tracker rằng node đã tải xong một torrent
    # pass
    info_hash = ""
    match = re.search(r"xt=urn:btih:([a-fA-F0-9]{40})", data["magnet_text"]) #Tìm kiếm thông tin hash từ magnet link
    if match:
        info_hash = match.group(1)
    else:
        message = {"status": "failed", "message": "Invalid magnet link"}
        client_socket.sendall(json.dumps(message).encode())
        return

    new_data = {
        "ip": data["node_ip"],
        "port": data["node_port"],
        "info_hash": info_hash,
    }

    peer_on_torrent.append(new_data) #Thêm thông tin của peer vào danh sách peer_on_torrent

#Trả về danh sách các torrents mà một node đã tải lên.
def list_torrents(data):
    ip = data["node_ip"]
    port = data["node_port"]

    # message = {"status": "success", "torrents": torrents}
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


while True:
    client_socket, addr = server_socket.accept()
    handle_client(client_socket)
    client_socket.close()
