import socket, time, logging
import state
import config


# Thay đổi cấu hình logging để ghi vào file thay vì console
logging.basicConfig(
    filename='chat_debug.log', # Ghi vào file này
    level=getattr(logging, config.LOG_LEVEL), 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def send_message(sock, ip, port, msg):
    if len(msg) > config.MAX_MESSAGE_LENGTH:
        logging.warning("Message too long, truncating")
        msg = msg[:config.MAX_MESSAGE_LENGTH]
    try:
        sock.sendto(msg.encode('utf-8'), (ip, port))
        logging.debug(f"Sent message: {msg}")
    except Exception as e:
        logging.error(f"Failed to send message: {e}")

def receive_chat(sock):
    while state.running:
        try:
            data, addr = sock.recvfrom(1024)
            msg = data.decode('utf-8', errors='ignore')
            
            # Chỉ log những tin nhắn KHÔNG PHẢI là ALIVE để tránh rác màn hình debug
            if not msg.startswith("ALIVE:"):
                logging.debug(f"Received from {addr}: {msg}")

            if msg.startswith("JOIN:"):
                user = msg.split(":", 1)[1]
                with state.data_lock:
                    state.online_users[user] = time.time()
                with state.buffer_lock:
                    state.message_buffer.append(f">> {user} đã tham gia")
            
            elif msg.startswith("LEAVE:"):
                user = msg.split(":", 1)[1]
                with state.data_lock:
                    state.online_users.pop(user, None)
                with state.buffer_lock:
                    state.message_buffer.append(f"<< {user} đã rời phòng")

            elif msg.startswith("ALIVE:"):
                # Xử lý ngầm, không thêm vào message_buffer, không logging
                user = msg.split(":", 1)[1]
                with state.data_lock:
                    state.online_users[user] = time.time()
            else:
                prefix = f"{state.USERNAME}:"
                if msg.startswith(prefix):
                    # Đây là tin nhắn loopback của chính mình, bỏ qua không hiện
                    logging.debug("Bỏ qua tin nhắn loopback của chính mình")
                    continue
                with state.buffer_lock:
                    state.message_buffer.append(msg)
                    if len(state.message_buffer) > config.MAX_BUFFER_SIZE:
                        state.message_buffer.pop(0)

        except socket.timeout:
            continue
        except Exception as e:
            logging.error(f"Error in receive_chat: {e}")
            break
