import socket
import threading
import json

class PongClient:
    def __init__(self, host='127.0.0.1', port=12345):
        self.host = host
        self.port = port
        self.sock = None
        self.running = False
        self.hand_message_client = None

    def connect(self, timeout=3.0):
        try:
            self.sock = socket.socket()
            self.sock.settimeout(timeout)
            self.sock.connect((self.host, self.port))
            self.sock.settimeout(None)
            self.running = True
            threading.Thread(target=self.listen, daemon=True).start()
            return True
        except Exception as e:
            print("[server core] connect ERROR", {e})
            return False

    def listen(self):
        buf = b''
        try:
            while self.running:
                data = self.sock.recv(4096)
                if not data:
                    break
                buf += data
                while b'\n' in buf:
                    line, buf = buf.split(b'\n',1)
                    if not line:
                        continue
                    try:
                        msg = json.loads(line.decode())
                    except:
                        continue
                    if self.hand_message_client:
                        try:
                            self.hand_message_client(msg)
                        except:
                            pass
        except:
            pass
        finally:
            self.running = False

    def send(self, json_data):
        if not self.running:
            return False
        try:
            self.sock.sendall((json.dumps(json_data) + "\n").encode())
            return True
        except:
            self.running = False
            return False

    def close(self):
        self.running = False
        try:
            self.sock.close()
        except:
            pass
