import sys
from PyQt6 import QtWidgets, QtCore, QtGui
from pong_client import PongClient

class GameWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.state = None
        self.nicks = []
        self.setMinimumSize(800, 400)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.fillRect(self.rect(), QtGui.QColor(25, 25, 25))

        if not self.state:
            qp.setPen(QtGui.QColor(180, 180, 180))
            qp.drawText(self.rect(), QtCore.Qt.AlignmentFlag.AlignCenter, "wait please")
            return

        st = self.state

        W = self.width()
        H = self.height()

        sx = W / st["width"]
        sy = H / st["height"]

        pen = QtGui.QPen(QtGui.QColor(90, 90, 90))
        pen.setStyle(QtCore.Qt.PenStyle.DashLine)
        qp.setPen(pen)
        qp.drawLine(W // 2, 0, W // 2, H)

        qp.setBrush(QtGui.QColor(230, 230, 230))
        qp.setPen(QtGui.QColor(230, 230, 230))

        paddle_h = st["paddle_h"] * sy
        paddle_w = 12 * sx

        x0 = st["paddle_x"][0] * sx
        y0 = st["paddles"][0] * sy
        qp.drawRect(QtCore.QRectF(x0, y0 - paddle_h / 2, paddle_w, paddle_h))

        x1 = st["paddle_x"][1] * sx
        y1 = st["paddles"][1] * sy
        qp.drawRect(QtCore.QRectF(x1, y1 - paddle_h / 2, paddle_w, paddle_h))

        bx = st["ball"]["x"] * sx
        by = st["ball"]["y"] * sy
        ball_r = 12 * ((sx + sy) / 2)

        qp.setBrush(QtGui.QColor("#ff99cc"))  # розовый
        qp.setPen(QtGui.QColor("#ff99cc"))
        qp.drawEllipse(QtCore.QRectF(bx - ball_r/2, by - ball_r/2, ball_r, ball_r))

        qp.setPen(QtGui.QColor(240, 240, 240))
        qp.setFont(QtGui.QFont("Arial", 24))
        qp.drawText(20, 40, str(st["scores"][0]))
        qp.drawText(W - 60, 40, str(st["scores"][1]))

        if "win_score" in st:
            qp.setFont(QtGui.QFont("Arial", 18))
            qp.setPen(QtGui.QColor("#ff66b2"))
            qp.drawText(
                0, 0, W, 80,
                QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignTop,
                f"Win: {st['win_score']}"
            )

        qp.setFont(QtGui.QFont("Arial", 12))
        qp.setPen(QtGui.QColor(200,200,200))
        left_name = self.nicks[0] if len(self.nicks) > 0 else "Player0"
        right_name = self.nicks[1] if len(self.nicks) > 1 else "Player1"
        try:
            qp.drawText(x0, 10, left_name)
            qp.drawText(x1, 10, right_name)
            qp.setPen(QtGui.QColor("#ff66b2"))
            qp.setFont(QtGui.QFont("Arial", 20, QtGui.QFont.Weight.Bold))
            win_text = f"До {st['win_score']}"
            qp.drawText(self.rect(), QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignHCenter, win_text)
        except:
            pass

class MsgEmitter(QtCore.QObject):
    msg = QtCore.pyqtSignal(dict)

class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.client = PongClient()
        if not self.client.connect():
            QtWidgets.QMessageBox.critical(self, "ERROR", "Не удалось подключиться")
            sys.exit(1)

        self.emitter = MsgEmitter()
        self.client.hand_message_client = self.emitter.msg.emit
        self.emitter.msg.connect(self.on_msg)

        self.current_room = None
        self.player_idx = None
        self.name_set = False

        self.init_ui()
        self.setFixedSize(360, 260)
        self.client.send({"action":"LIST"})

        self.setStyleSheet("""
            QWidget {
                background-color: #ffe6f2;
                color: #333;
                font-size: 14px;
            }

            QLineEdit {
                background-color: white;
                border: 2px solid #ffb3d9;
                border-radius: 6px;
                padding: 4px;
            }

            QPushButton {
                background-color: #ffb3d9;
                border: none;
                border-radius: 6px;
                padding: 8px 14px;
                color: white;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #ff99cc;
            }

            QPushButton:pressed {
                background-color: #ff80bf;
            }

            QListWidget {
                background-color: white;
                border: 2px solid #ffb3d9;
                border-radius: 6px;
            }

            QLabel {
                font-weight: bold;
            }
        """)

    def init_ui(self):
        self.setWindowTitle("lobby")

        self.stacked = QtWidgets.QStackedWidget()
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(self.stacked)

        page_nick = QtWidgets.QWidget()
        v0 = QtWidgets.QVBoxLayout(page_nick)
        lbl = QtWidgets.QLabel("NICKNAME")
        lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        lbl.setFont(QtGui.QFont("Arial", 18))
        self.input_nick = QtWidgets.QLineEdit()
        self.input_nick.setFixedWidth(300)
        self.input_nick.setPlaceholderText("vvedite nickname")
        btn_nick_ok = QtWidgets.QPushButton("продолжить")
        v0.addStretch(1)
        v0.addWidget(lbl, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        v0.addWidget(self.input_nick, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        v0.addWidget(btn_nick_ok, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        v0.addStretch(2)
        self.stacked.addWidget(page_nick)

        page_lobby = QtWidgets.QWidget()
        h = QtWidgets.QHBoxLayout(page_lobby)

        left = QtWidgets.QVBoxLayout()
        lbl_rooms = QtWidgets.QLabel("ROOMS")
        lbl_rooms.setFont(QtGui.QFont("Arial", 14))
        self.rooms_list = QtWidgets.QListWidget()
        left.addWidget(lbl_rooms)
        left.addWidget(self.rooms_list)
        left.addStretch(1)

        right = QtWidgets.QVBoxLayout()
        lbl_controls = QtWidgets.QLabel("setting:")
        lbl_controls.setFont(QtGui.QFont("Arial", 14))
        right.addWidget(lbl_controls)

        form = QtWidgets.QFormLayout()
        self.room_name_edit = QtWidgets.QLineEdit()
        self.win_edit = QtWidgets.QLineEdit()
        self.win_edit.setFixedWidth(80)
        self.win_edit.setText("10")
        form.addRow("ROOMS NAME", self.room_name_edit)
        form.addRow("win score:", self.win_edit)
        right.addLayout(form)

        self.btn_create = QtWidgets.QPushButton("create room")
        self.btn_join = QtWidgets.QPushButton("come in room")
        self.btn_leave = QtWidgets.QPushButton("leave room")
        self.btn_refresh = QtWidgets.QPushButton("refresh list")

        grid = QtWidgets.QGridLayout()
        grid.addWidget(self.btn_create, 0, 0)
        grid.addWidget(self.btn_join, 0, 1)
        grid.addWidget(self.btn_leave, 1, 0)
        grid.addWidget(self.btn_refresh, 1, 1)

        right.addLayout(grid)
        right.addStretch(1)

        right.addWidget(self.btn_create)
        right.addWidget(self.btn_join)
        right.addWidget(self.btn_leave)
        right.addStretch(1)
        right.addWidget(self.btn_refresh)

        h.addLayout(left, 2)
        h.addLayout(right, 1)

        self.stacked.addWidget(page_lobby)

        page_game = QtWidgets.QWidget()
        vgame = QtWidgets.QVBoxLayout(page_game)
        self.game_widget = GameWidget()
        vgame.addWidget(self.game_widget)
        self.btn_back = QtWidgets.QPushButton("leave play")
        vgame.addWidget(self.btn_back, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.stacked.addWidget(page_game)

        btn_nick_ok.clicked.connect(self.on_nick_continue)
        self.btn_create.clicked.connect(self.on_create)
        self.btn_join.clicked.connect(self.on_join)
        self.btn_leave.clicked.connect(self.on_leave)
        self.btn_refresh.clicked.connect(lambda: self.client.send({"action":"LIST"}))
        self.rooms_list.itemDoubleClicked.connect(self.on_list_double)
        self.btn_back.clicked.connect(self.on_back_from_game)

        self.stacked.setCurrentIndex(0)

    def on_nick_continue(self):
        name = self.input_nick.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, "ERROR", "введите никнейм")
            return
        self.client.send({"action":"SET_NAME", "name": name})

    def on_create(self):
        if not self.name_set:
            QtWidgets.QMessageBox.warning(self, "ERROR", "установите никнейм")
            return
        rn = self.room_name_edit.text().strip()
        if not rn:
            QtWidgets.QMessageBox.warning(self, "ERROR", "введите имя комнаты")
            return
        try:
            w = int(self.win_edit.text().strip())
        except:
            w = 10
        w = max(1, min(99, w))
        self.client.send({"action":"CREATE", "room": rn, "win_score": w})

    def on_join(self):
        if not self.name_set:
            QtWidgets.QMessageBox.warning(self, "ERROR", "сначала установите никнейм")
            return
        rn = self.room_name_edit.text().strip()
        if not rn:
            item = self.rooms_list.currentItem()
            if not item:
                QtWidgets.QMessageBox.warning(self, "ERROR", "выберите комнату или введите имя")
                return
            rn = item.text()
        self.client.send({"action":"JOIN", "room": rn})

    def on_leave(self):
        self.client.send({"action":"LEAVE"})
        self.current_room = None
        self.player_idx = None
        self.game_widget.state = None
        self.stacked.setCurrentIndex(1)

    def on_list_double(self, it):
        text = it.text()
        rn = text.split("  ")[0]
        self.room_name_edit.setText(rn)
        self.client.send({"action": "JOIN", "room": rn})

    def on_back_from_game(self):
        if self.current_room:
            try:
                self.client.send({"action":"LEAVE"})
            except:
                pass
        self.current_room = None
        self.player_idx = None
        self.game_widget.state = None
        self.stacked.setCurrentIndex(1)

    @QtCore.pyqtSlot(dict)
    def on_msg(self, m):
        t = m.get("type")

        if t == "WELCOME":
            return

        if t == "ROOMS":
            self.rooms_list.clear()
            for room in m.get("rooms", []):
                name = room["name"]
                ws = room["win_score"]
                self.rooms_list.addItem(f"{name}  (win {ws})")

            return

        if t == "NAME_TAKEN":
            QtWidgets.QMessageBox.warning(self, "Ник занят", f"{m.get('name')} buzy")
            return

        if t == "NAME_SET":
            self.name_set = True
            self.input_nick.setEnabled(False)
            QtWidgets.QMessageBox.information(self, "ОК", f"set {m.get('name')}")

            QtCore.QTimer.singleShot(0, lambda: self.stacked.setCurrentIndex(1))
            QtCore.QTimer.singleShot(0, lambda: self.resize(1000, 640))
            self.setFixedSize(QtCore.QSize())
            self.resize(1000, 640)

            self.client.send({"action":"LIST"})
            return

        if t == "CREATED":
            rn = m.get("room")
            if rn:
                self.client.send({"action":"JOIN", "room": rn})
            return

        if t == "JOINED":
            self.current_room = m.get("room")
            self.player_idx = m.get("player")
            ws = m.get("win_score", 10)
            self.win_edit.setText(str(ws))
            self.setWindowTitle(f"PONG {self.current_room} # player {self.player_idx + 1}")
            QtCore.QTimer.singleShot(0, lambda: self.stacked.setCurrentIndex(1))
            return

        if t == "LEFT":
            self.current_room = None
            self.player_idx = None
            self.game_widget.state = None
            QtWidgets.QMessageBox.information(self, "lol", "you leave room")

            self.client.send({"action":"LIST"})
            return

        if t == "STATE":
            st = m.get("state")
            self.game_widget.state = st
            if st.get("playing", False):
                self.stacked.setCurrentIndex(2)
            self.game_widget.update()
            return

        if t == "WIN":
            QtWidgets.QMessageBox.information(self, "WIN", f"player {m.get('winner')} winner!")
            try:
                self.client.send({"action":"LEAVE"})
            except:
                pass
            self.current_room = None
            self.player_idx = None
            self.stacked.setCurrentIndex(1)
            self.client.send({"action":"LIST"})
            return

        if t == "OPPONENT_LEFT":
            QtWidgets.QMessageBox.information(self, "Выход", "your opponent leave")

            self.current_room = None
            self.player_idx = None
            self.game_widget.state = None
            self.stacked.setCurrentIndex(1)
            self.client.send({"action": "LIST"})
            return

        if t == "ERROR":
            QtWidgets.QMessageBox.warning(self, "ERROR", m.get("message", ""))
            return

    def keyPressEvent(self, e):
        if not self.current_room:
            return
        k = e.key()
        if k in (QtCore.Qt.Key.Key_Up, QtCore.Qt.Key.Key_W):
            self.client.send({"action":"INPUT", "dir": "up"})
        elif k in (QtCore.Qt.Key.Key_Down, QtCore.Qt.Key.Key_S):
            self.client.send({"action":"INPUT", "dir": "down"})

    def keyReleaseEvent(self, e):
        if self.current_room:
            self.client.send({"action":"INPUT", "dir": "stop"})

    def closeEvent(self, e):
        try:
            self.client.send({"action":"LEAVE"})
        except:
            pass
        self.client.close()
        e.accept()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
