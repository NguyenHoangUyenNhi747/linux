import time
import state
import config
import control

def heartbeat(sock, ip, port):
    while state.running:
        try:
            # Gửi tin nhắn định danh ngầm
            sock.sendto(f"ALIVE:{state.USERNAME}".encode(), (ip, port))
        except:
            pass
        time.sleep(3)

def check_timeout():
    while state.running:
        now = time.time()
        with state.data_lock:
            # list() tạo bản sao để tránh lỗi khi dictionary thay đổi kích thước
            for user, last in list(state.online_users.items()):
                if now - last > 5:
                    state.online_users.pop(user)
                    with state.buffer_lock:
                        state.message_buffer.append(f"-- {user} đã thoát (timeout)")
        time.sleep(5)
        

def broadcast_groups():
    """danh sách phòng hiện có"""
    while True:
        with state.data_lock:
            for name, info in state.groups.items():
                # Không gửi lại phòng mặc định vì ai cũng có sẵn
                if name != config.DEFAULT_GROUP_NAME:
                    msg = f"GROUP_CREATE:{name}:{info['ip']}:{info['port']}"
                    control.send_control(msg)
        time.sleep(5)

