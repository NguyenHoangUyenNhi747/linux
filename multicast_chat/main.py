import threading, curses, socket, struct, sys, time
import state
from config import *
from control import receive_control, send_control
from network import receive_chat, send_message
from logic import heartbeat, check_timeout, broadcast_groups
from ui import menu_ui, chat_ui

def main():
    state.USERNAME = input("Who are you? ").strip() or "User"

    if DEFAULT_GROUP_NAME not in state.groups:
        state.groups[DEFAULT_GROUP_NAME] = {
            "ip": DEFAULT_GROUP_IP, "port": DEFAULT_GROUP_PORT, "users": set()
        }
    
    threading.Thread(target=receive_control, daemon=True).start()
    threading.Thread(target=broadcast_groups, daemon=True).start()

    while True:
        choice = curses.wrapper(menu_ui, state.groups)

        if choice == "Exit": sys.exit(0)

        if choice.startswith("CREATE:"):
            curses.def_shell_mode()
            name = input("Tên nhóm: ").strip()
            curses.reset_shell_mode()
            if name and name not in state.groups:
                new_id = len(state.groups) + 1
                ip, port = f"239.255.0.{new_id}", 5000 + new_id
                state.groups[name] = {"ip": ip, "port": port, "users": set()}
                send_control(f"GROUP_CREATE:{name}:{ip}:{port}")
                choice = name
            else: continue

        # Gán thông tin phòng
        state.group_name = choice
        state.group_ip = state.groups[choice]["ip"]
        state.group_port = state.groups[choice]["port"]

        # Thiết lập Socket
        state.chat_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        state.chat_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            state.chat_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except: pass

        state.chat_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
        
        state.chat_sock.bind(("", state.group_port))
        
        mreq = struct.pack("4sl", socket.inet_aton(state.group_ip), socket.INADDR_ANY)
        state.chat_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        
        state.running = True
        state.message_buffer.clear()
        state.online_users.clear()
        
        send_message(state.chat_sock, state.group_ip, state.group_port, f"JOIN:{state.USERNAME}")

        # Chạy thread
        threading.Thread(target=receive_chat, args=(state.chat_sock,), daemon=True).start()
        threading.Thread(target=heartbeat, args=(state.chat_sock, state.group_ip, state.group_port), daemon=True).start()
        threading.Thread(target=check_timeout, daemon=True).start()

        curses.wrapper(chat_ui)
        state.running = False
        try:
            state.chat_sock.sendto(f"LEAVE:{state.USERNAME}".encode(), (state.group_ip, state.group_port))
            state.chat_sock.close()
        except: pass

if __name__ == "__main__":
    main()
