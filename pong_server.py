import socket
import json
import threading
import time
from pong_logic import GameState

FPS = 30
TICK = 1 / FPS

HOST = "0.0.0.0"
PORT = 12345

def send_json(conn, obj):
    try:
        conn.sendall((json.dumps(obj) + "\n").encode())
    except:
        raise

class Room:
    def __init__(self, name, win_score=10, server=None):
        self.name = name
        self.clients = []
        self.inputs = {}
        self.server = server
        self.state = GameState()
        self.running = False
        self.win_score = win_score

    def start(self):
        if self.running:
            return

        self.running = True
        self.state.win_score = self.win_score
        self.state.winner = None
        self.state.scores = [0, 0]
        self.state.playing = True
        self.state.velocity_ball(1)

        print(f"[server core] ROOM {self.name} start # win_score={self.win_score}")

        threading.Thread(target=self.loop, daemon=True).start()

    def loop(self):
        last = time.time()

        while self.running:
            now = time.time()
            dt = now - last
            last = now

            try:
                self.state.update(dt, self.inputs)
            except Exception as e:
                print(f"[server core] {self.name} game over with ERROR", e)

            self.broadcast_state()

            if self.state.winner is not None:
                print(f"[server core] {self.name} # winner {self.state.winner}")

                for conn, lol in list(self.clients):
                    try:
                        send_json(conn, {"type": "WIN", "winner": self.state.winner + 1})
                    except:
                        pass

                self.running = False
                self.state.playing = False
                self.inputs = {}
                return

            sleep_t = TICK - (time.time() - now)
            if sleep_t > 0:
                time.sleep(sleep_t)

    def broadcast_state(self):
        nicks = ['']
        if self.server is not None:
            for conn, index in self.clients:
                name = self.server.client_names.get(conn)
                if name is None:
                    name =  f"player{index + 1}"
                nicks.append(name)
        else:
            for conn, index in self.clients:
                nicks.append(f"player{index + 1}")
        msg = {"type": "STATE", "state": self.state.to_dict(), "room": self.name, "nicks": nicks}
        for conn, lol in list(self.clients):
            try:
                send_json(conn, msg)
            except:
                pass

    def remove_client(self, conn):
        remove_index = None

        for pair in self.clients:
            client_conn = pair[0]
            player_index = pair[1]

            if client_conn == conn:
                remove_index = player_index
                self.clients.remove(pair)
                break

        if remove_index is not None and len(self.clients) == 1:
            other_conn, other_index = self.clients[0]
            try:
                send_json(other_conn, {"type": "OPPONENT_LEFT"})
            except:
                pass

        if len(self.clients) < 2:
            self.running = False
            self.state.playing = False
            self.inputs = {}

class PongServer:
    def __init__(self):
        self.rooms = {}
        self.clients = []
        self.client_names = {}

    def broadcast_room_list(self):
        payload = {"type": "ROOMS", "rooms": [ {"name": rname, "win_score": self.rooms[rname].win_score} for rname in self.rooms] }
        dead = []
        for c in list(self.clients):
            try:
                send_json(c, payload)
            except:
                dead.append(c)
        for d in dead:
            if d in self.clients:
                self.clients.remove(d)

    def start(self):
        server_socket = socket.socket()
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen(228)
        print(f"[server core] server listening on {HOST}:{PORT}")

        try:
            while True:
                conn, addr = server_socket.accept()
                print(f"[server core] {addr} connect")
                self.clients.append(conn)
                threading.Thread(target=self.client_thread, args=(conn,), daemon=True).start()
        finally:
            server_socket.close()

    def client_thread(self, conn):
        buffer = b""
        current_room = None
        player_index = None

        send_json(conn, {"type": "WELCOME", "msg": "pong"})

        try:
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                buffer += data

                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if not line:
                        continue
                    try:
                        msg = json.loads(line.decode())
                    except:
                        continue

                    act = msg.get("action")

                    # name
                    if act == "SET_NAME":
                        name = msg.get("name", "").strip()
                        if not name:
                            send_json(conn, {"type": "ERROR", "message": "empty name"})
                            continue

                        taken = False
                        for c, n in self.client_names.items():
                            if n == name and c != conn:
                                taken = True
                                break

                        if taken:
                            send_json(conn, {"type": "NAME_TAKEN", "name": name})
                            print(f"[server core] take buzy {name}")
                        else:
                            self.client_names[conn] = name
                            send_json(conn, {"type": "NAME_SET", "name": name})
                            print(f"[server core] identify {name} ot {conn}")
                        continue

                    # list rooms
                    elif act == "LIST":
                        self.broadcast_room_list()
                        continue

                    # create room
                    elif act == "CREATE":
                        name = msg.get("room")
                        win_value = msg.get("win_score", 10)

                        if not name:
                            send_json(conn, {"type": "ERROR", "message": "no room name"})
                            continue

                        if name in self.rooms:
                            send_json(conn, {"type": "ERROR", "message": "room exists"})
                            continue

                        try:
                            win_value = int(win_value)
                        except:
                            win_value = 10
                        win_value = max(1, min(99, win_value))

                        self.rooms[name] = Room(name, win_value, self)

                        print(f"[server core] {name} create # winscore {win_value}")

                        send_json(conn, {"type": "CREATED", "room": name})
                        self.broadcast_room_list()
                        continue

                    # join client in room
                    elif act == "JOIN":
                        name = msg.get("room")
                        if name not in self.rooms:
                            send_json(conn, {"type": "ERROR", "message": "room not found"})
                            continue

                        rm = self.rooms[name]

                        if any(c == conn for c, lol in rm.clients):
                            send_json(conn, {"type": "ERROR", "message": "already in room"})
                            continue

                        if len(rm.clients) >= 2:
                            send_json(conn, {"type": "ERROR", "message": "room full"})
                            continue

                        used = [i for lol, i in rm.clients]
                        index = 0 if 0 not in used else 1

                        rm.clients.append((conn, index))
                        rm.inputs[index] = "stop"

                        current_room = rm
                        player_index = index

                        send_json(conn, {
                            "type": "JOINED",
                            "room": name,
                            "player": index,
                            "win_score": rm.win_score
                        })

                        self.broadcast_room_list()
                        rm.broadcast_state()
                        if len(rm.clients) == 2 and not rm.running:
                            rm.start()
                        continue

                    # leave room from player
                    elif act == "LEAVE":
                        if current_room:
                            current_room.remove_client(conn)
                            send_json(conn, {"type": "LEFT"})
                            current_room = None
                            player_index = None
                            self.broadcast_room_list()
                        else:
                            send_json(conn, {"type": "ERROR", "message": "not in room"})
                        continue

                    elif act == "INPUT":
                        if current_room and player_index is not None:
                            d = msg.get("dir", "stop")
                            current_room.inputs[player_index] = d
                        else:
                            send_json(conn, {"type": "ERROR", "message": "not in room"})
                        continue

                    else:
                        send_json(conn, {"type": "ERROR", "message": "unknown action"})
                        continue

        except Exception as e:
            print("[server core] haha lol", e)

        try:
            if current_room:
                current_room.remove_client(conn)
                self.broadcast_room_list()
        except:
            pass

        try:
            if conn in self.client_names:
                del self.client_names[conn]
        except:
            pass

        try:
            if conn in self.clients:
                self.clients.remove(conn)
        except:
            pass

        try:
            conn.close()
        except:
            pass


if __name__ == "__main__":
    PongServer().start()
