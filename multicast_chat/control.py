# control.py
import socket, struct
import config # Thay đổi cách import để rõ ràng hơn
import state

def setup_control_socket():
    # Sử dụng config.CONTROL_PORT để tránh lỗi NameError
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except:
        pass

    # Gọi trực tiếp từ module config
    sock.bind(("", config.CONTROL_PORT))

    mreq = struct.pack("4sl", socket.inet_aton(config.CONTROL_IP), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    sock.settimeout(1)
    return sock

# Đưa dòng này xuống cuối cùng
control_sock = setup_control_socket()

def send_control(msg):
    try:
        control_sock.sendto(msg.encode(), (config.CONTROL_IP, config.CONTROL_PORT))
    except:
        pass

def receive_control():
    while True:
        try:
            data, _ = control_sock.recvfrom(1024)
            msg = data.decode()
            if msg.startswith("GROUP_CREATE:"):
                parts = msg.split(":")
                if len(parts) == 4:
                    _, name, ip, port = parts
                    with state.data_lock:
                        if name not in state.groups:
                            state.groups[name] = {
                                "ip": ip, 
                                "port": int(port), 
                                "users": set()
                            }
        except:
            continue
