import threading
import queue
import spotify

class ControllerThread(threading.Thread):

    def __init__(self, out_queue):
        self.router = {
            'login': self.login,
            'logout': self.logout,
            'album': self.get_album,
            'exit': self.exit
        }
        self.in_queue = queue.Queue()
        self.out_queue = out_queue
        self.session = spotify.Session()
        self.active = True

    def run(self):
        while self.active:
            self.execute_command()
                
    def execute_command(self):
        try:
            command = self.in_queue.get_nowait()
            opcode = command.opcode
            args = command.args
            self.router[opcode](*args)
        except queue.Empty:
            pass

    def login(self, username, password): 
        pass

    def logout(self):
        pass

    def get_album(self, album_id):
        pass

    def exit(self):
        self.active = False
