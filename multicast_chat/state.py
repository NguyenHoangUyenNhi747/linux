import threading

groups = {}
USERNAME = None
group_name = None
group_ip = None
group_port = None
chat_sock = None
running = False
online_users = {}
message_buffer = []

data_lock = threading.Lock()
buffer_lock = threading.Lock()
