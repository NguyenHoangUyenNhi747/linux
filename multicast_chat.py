import socket, struct, threading, time, curses, sys

CONTROL_IP = "224.1.1.100"
CONTROL_PORT = 6000

DEFAULT_GROUP_NAME = "Phòng Chung"
DEFAULT_GROUP_IP = "224.1.1.1"
DEFAULT_GROUP_PORT = 5001

groups = {
    DEFAULT_GROUP_NAME: {
        "ip": DEFAULT_GROUP_IP,
        "port": DEFAULT_GROUP_PORT,
        "users": set()
    }
}

USERNAME = ""
group_name = ""
group_ip = ""
group_port = 0

running = False
chat_sock = None

online_users = {}      # {user: last_seen}
message_buffer = []   # list[str]

data_lock = threading.Lock()
def setup_control_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", CONTROL_PORT))
    mreq = struct.pack("4sl", socket.inet_aton(CONTROL_IP), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    sock.settimeout(1)
    return sock

control_sock = setup_control_socket()

def send_control(msg):
    try:
        control_sock.sendto(msg.encode(), (CONTROL_IP, CONTROL_PORT))
    except:
        pass

def receive_control():
    while True:
        try:
            data, _ = control_sock.recvfrom(1024)
            msg = data.decode()

            if msg.startswith("GROUP_CREATE:"):
                _, name, ip, port = msg.split(":")
                if name not in groups:
                    groups[name] = {
                        "ip": ip,
                        "port": int(port),
                        "users": set()
                    }
        except socket.timeout:
            continue
        except:
            pass
def send_chat(msg):
    if chat_sock:
        try:
            chat_sock.sendto(msg.encode(), (group_ip, group_port))
        except:
            pass
def receive_chat():
    global running
    while running:
        try:
            data, _ = chat_sock.recvfrom(1024)
            msg = data.decode()

            with data_lock:
                if msg.startswith("JOIN:"):
                    user = msg.split(":",1)[1]
                    online_users[user] = time.time()
                    groups[group_name]["users"].add(user)
                    message_buffer.append(f">> {user} joined")

                    if user != USERNAME:
                        send_chat(f"HELLO:{USERNAME}")

                elif msg.startswith("HELLO:") or msg.startswith("ALIVE:"):
                    user = msg.split(":",1)[1]
                    online_users[user] = time.time()
                    groups[group_name]["users"].add(user)

                elif msg.startswith("LEAVE:"):
                    user = msg.split(":",1)[1]
                    online_users.pop(user, None)
                    groups[group_name]["users"].discard(user)
                    message_buffer.append(f"<< {user} left")

                else:
                    message_buffer.append(msg)

                if len(message_buffer) > 500:
                    message_buffer.pop(0)

        except socket.timeout:
            continue
        except:
            break
def heartbeat():
    while running:
        send_chat(f"ALIVE:{USERNAME}")
        time.sleep(5)
def check_timeout():
    while running:
        time.sleep(5)
        now = time.time()

        with data_lock:
            to_remove = [
                u for u,t in online_users.items()
                if u != USERNAME and now - t > 15
            ]

            for u in to_remove:
                online_users.pop(u, None)
                groups[group_name]["users"].discard(u)
                message_buffer.append(f"!! {u} timeout")
def chat_ui(stdscr):
    global running

    curses.curs_set(1)
    stdscr.nodelay(True)

    h, w = stdscr.getmaxyx()
    pad = curses.newpad(1000, w)
    scroll = 0
    input_buf = ""

    send_chat(f"JOIN:{USERNAME}")

    while running:
        stdscr.clear()

        with data_lock:
            stdscr.addstr(
                0, 0,
                f" Group: {group_name} | User: {USERNAME} | Online: {len(online_users)} ".ljust(w),
                curses.A_REVERSE
            )

            for i, line in enumerate(message_buffer):
                pad.addstr(i, 0, line[:w-1])

        pad.refresh(scroll, 0, 2, 0, h-3, w-1)

        stdscr.addstr(h-1, 0, "> " + input_buf)
        stdscr.refresh()

        try:
            ch = stdscr.getch()
        except:
            ch = -1

        if ch in (10,13):
            msg = input_buf.strip()
            input_buf = ""

            if msg == "/exit":
                send_chat(f"LEAVE:{USERNAME}")
                running = False
                break
            elif msg == "/online":
                with data_lock:
                    message_buffer.append(
                        "Online: " + ", ".join(online_users.keys())
                    )
            elif msg:
                send_chat(f"[{time.strftime('%H:%M')}] {USERNAME}: {msg}")

        elif ch in (127,8):
            input_buf = input_buf[:-1]
        elif 32 <= ch <= 126:
            input_buf += chr(ch)
def menu_ui(stdscr):
    curses.curs_set(0)
    idx = 0

    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()

        stdscr.addstr(1, 2, "=== MULTICAST CHAT ===", curses.A_BOLD)

        items = list(groups.keys()) + ["+ Create new group", "Exit"]

        for i, it in enumerate(items):
            attr = curses.A_REVERSE if i == idx else 0
            stdscr.addstr(4+i, 4, it, attr)

        key = stdscr.getch()

        if key == curses.KEY_UP and idx > 0:
            idx -= 1
        elif key == curses.KEY_DOWN and idx < len(items)-1:
            idx += 1
        elif key in (10,13):
            sel = items[idx]

            if sel == "+ Create new group":
                curses.echo()
                stdscr.addstr(h-2, 2, "New group name: ")
                name = stdscr.getstr(h-2, 20, 20).decode().strip()
                curses.noecho()
                if name:
                    return f"CREATE:{name}"
            else:
                return sel
def main():
    global USERNAME, group_name, group_ip, group_port, chat_sock, running

    USERNAME = input("Who are you? ").strip() or "User"

    threading.Thread(target=receive_control, daemon=True).start()

    while True:
        choice = curses.wrapper(menu_ui)

        if choice == "Exit":
            sys.exit(0)

        if choice.startswith("CREATE:"):
            name = choice.split(":",1)[1]
            idx = len(groups) + 1
            ip = f"224.1.1.{idx}"
            port = 5000 + idx
            groups[name] = {"ip": ip, "port": port, "users": set()}
            send_control(f"GROUP_CREATE:{name}:{ip}:{port}")
            continue

        group_name = choice
        group_ip = groups[choice]["ip"]
        group_port = groups[choice]["port"]

        chat_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        chat_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        chat_sock.bind(("", group_port))
        mreq = struct.pack("4sl", socket.inet_aton(group_ip), socket.INADDR_ANY)
        chat_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        chat_sock.settimeout(1)

        running = True
        online_users.clear()
        message_buffer.clear()
        online_users[USERNAME] = time.time()

        threading.Thread(target=receive_chat, daemon=True).start()
        threading.Thread(target=heartbeat, daemon=True).start()
        threading.Thread(target=check_timeout, daemon=True).start()

        curses.wrapper(chat_ui)

        running = False
        chat_sock.close()

