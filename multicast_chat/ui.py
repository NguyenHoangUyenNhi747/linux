import curses, time, logging
import state
import config
import network

logging.basicConfig(level=getattr(logging, config.LOG_LEVEL))

def menu_ui(stdscr, groups):
    curses.curs_set(0)
    # Nếu không có phím nhấn, hàm getch() sẽ chờ tối đa 1000ms (1 giây)
    stdscr.timeout(1000) 
    
    current_row = 0
    
    while True:
        stdscr.erase() # Dùng erase thay cho clear để tránh nháy màn hình
        height, width = stdscr.getmaxyx()
        
        # QUAN TRỌNG: Cập nhật lại danh sách nhóm từ state.groups ở mỗi vòng lặp
        group_list = list(groups.keys())
        
        # Đảm bảo current_row không bị tràn nếu danh sách nhóm thay đổi
        if current_row >= len(group_list):
            current_row = max(0, len(group_list) - 1)

        title = "CHỌN NHÓM CHAT"
        stdscr.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD)
        
        for idx, group in enumerate(group_list):
            if idx == current_row:
                stdscr.attron(curses.A_REVERSE)
            
            # Giới hạn hiển thị nếu tên nhóm quá dài
            stdscr.addstr(idx + 2, 2, f"> {group}"[:width-5])
            
            if idx == current_row:
                stdscr.attroff(curses.A_REVERSE)
        
        stdscr.addstr(height - 2, 2, "C: Tạo nhóm | Q: Thoát | Enter: Vào phòng")
        stdscr.refresh()
        
        key = stdscr.getch()
        
        # Nếu timeout 1s trôi qua mà không nhấn phím, key sẽ là -1
        if key == -1:
            continue # Vòng lặp chạy lại, cập nhật group_list mới

        if key == curses.KEY_UP and current_row > 0:
            current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(group_list) - 1:
            current_row += 1
        elif key in [ord('c'), ord('C')]:
            return "CREATE:"
        elif key in [ord('q'), ord('Q')]:
            return "Exit"
        elif key in [ord('\n'), 10, 13]:
            if group_list: # Tránh lỗi nếu danh sách trống
                return group_list[current_row]


def chat_ui(stdscr):
    # Khởi tạo màu sắc (nếu muốn)
    if curses.has_colors():
        curses.start_color()
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK) # Màu cho "You"

    stdscr.nodelay(True)
    curses.curs_set(1)
    height, width = stdscr.getmaxyx()
    
    chat_width = (width * 3) // 4
    user_list_width = width - chat_width
    
    chat_win = curses.newwin(height - 4, chat_width, 0, 0)
    user_win = curses.newwin(height - 4, user_list_width, 0, chat_width)
    input_win = curses.newwin(3, width, height - 3, 0)
    
    chat_win.scrollok(True)
    input_buffer = ""

    while state.running:
        try:
            # 1. VẼ KHUNG CHAT
            chat_win.erase()
            chat_win.border(0)
            chat_win.addstr(0, 2, f" Nhóm: {state.group_name} ", curses.A_BOLD)
            
            with state.buffer_lock:
                display_msgs = state.message_buffer[-(height - 6):]
                for i, msg in enumerate(display_msgs):
                    # Giới hạn chiều dài tin nhắn để không gây lỗi addstr
                    safe_msg = msg[:chat_width - 4]
                    
                    if msg.startswith("You:"):
                        start_x = max(1, chat_width - len(safe_msg) - 2)
                        chat_win.addstr(i + 1, start_x, safe_msg, curses.color_pair(1) if curses.has_colors() else curses.A_NORMAL)
                    else:
                        chat_win.addstr(i + 1, 1, safe_msg)
            chat_win.refresh()

            # 2. VẼ DANH SÁCH USER
            user_win.erase()
            user_win.border(0)
            user_win.addstr(0, 1, " Online ", curses.A_BOLD)
            with state.data_lock:
                users = list(state.online_users.keys())
                for idx, user in enumerate(users[:height-6]):
                    u_display = f"* {user}" if user == state.USERNAME else f"  {user}"
                    user_win.addstr(idx + 1, 1, u_display[:user_list_width - 2])
            user_win.refresh()

            # 3. VẼ KHUNG NHẬP LIỆU
            input_win.erase()
            input_win.border(0)
            prompt = " Tin nhắn: "
            # Chỉ hiển thị đoạn cuối nếu tin nhắn đang nhập quá dài
            visible_text = input_buffer[-(width - len(prompt) - 5):]
            input_win.addstr(1, 1, prompt + visible_text)
            input_win.refresh()

            # 4. XỬ LÝ PHÍM
            key = stdscr.getch()
            if key == -1:
                time.sleep(0.02)
                continue
            
            if key == ord('\n'):
                clean_msg = input_buffer.strip()
                if clean_msg:
                    # Gửi tin nhắn thực tế qua mạng
                    network.send_message(state.chat_sock, state.group_ip, state.group_port, f"{state.USERNAME}: {clean_msg}")
                    # Thêm vào buffer local để hiển thị ngay bên phải
                    with state.buffer_lock:
                        state.message_buffer.append(f"You: {clean_msg}")
                        if len(state.message_buffer) > config.MAX_BUFFER_SIZE:
                            state.message_buffer.pop(0)
                input_buffer = ""
            elif key == 27: # ESC để thoát ra menu
                state.running = False
            elif key in [curses.KEY_BACKSPACE, 127, 8]:
                input_buffer = input_buffer[:-1]
            elif 32 <= key <= 126:
                input_buffer += chr(key)
                
        except curses.error:
            # Nếu lỗi do vẽ màn hình (như resize cửa sổ quá nhỏ), bỏ qua thay vì thoát app
            pass
        except Exception as e:
            # Log lỗi khác vào file thay vì làm sập app
            logging.error(f"UI Loop Error: {e}")
            continue

    curses.curs_set(0)

