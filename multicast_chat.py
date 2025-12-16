import socket
import struct
import threading
import time

MULTICAST_GROUP = '224.1.1.1'
MULTICAST_PORT = 5007
USERNAME = input("enter your name: ")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('', MULTICAST_PORT))

mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_GROUP), socket.INADDR_ANY)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)


online_user = {}


def send_message(msg):
	sock.sendto(msg.encode('utf-8'), (MULTICAST_GROUP, MULTICAST_PORT))

def receive_message():
	while True:
		try:
			data, addr = sock.recvfrom(1024)
			msg = data.decode('utf-8')
			
			if msg.startswith("JOIN:"):
				user = msg.split(":",1)[1]
				online_user[user] = time.time()
				if user!= USERNAME:
				    print(f"\n>> {user} joined the chat")
				    send_message(f"HELLO:{USERNAME}")
			elif msg.startswith("HELLO"):
			    user = msg.split(":",1)[1]
			    online_user[user] = time.time()
			elif msg.startswith("LEAVE:"):
				user = msg.split(":",1)[1]
				if user in online_user:
				    online_user.pop(user)
				print(f"\n>> {user} left the chat")
			elif msg.startswith("ALIVE:"):
			    user = msg.split(":",1)[1]
			    online_user[user] = time.time()
			else:
				print (f"\n>> {msg}")
		except Exception as e:
			print ("Error:", e)

def heartbeat():
	while True:
		time.sleep(5)
		send_message(f"ALIVE:{USERNAME}")
		
def check_timeout():
    while True:
        time.sleep(5)
        now = time.time()
        to_remove =[]
        for user, last_time in online_user.items():
            if now - last_time >10:
                to_remove.append(user)
        for user in to_remove:
            online_user.pop(user)
            print(f"\n>> {user} seems to have left (interrupt)")

threading.Thread(target=receive_message, daemon=True).start()
threading.Thread(target=heartbeat, daemon=True).start()
threading.Thread(target=check_timeout, daemon=True).start()

send_message(f"JOIN:{USERNAME}")

try:
	while True:
		msg = input()
		if msg.lower() == "/exit":
			send_message(f"LEAVE:{USERNAME}")
			break
		elif msg.lower() == "/online":
		    users = ", ".join(online_user.keys())
		    print(f"user online: {users}")
		else:
		    send_message(f"{USERNAME}: {msg}")
except KeyboardInterrupt:
	send_message(f"LEAVE:{USERNAME}")
