import zmq
import threading
import queue
import spotify

class ControllerThread(threading.Thread):

    def __init__(self, out_queue):
        router = {
            'login': self.login,
            'logout': self.logout,
            'album': self.get_album
        }
        self.in_queue = queue.Queue()
        self.out_queue = out_queue
        self.session = spotify.Session()

    def login(self, username, password): 
        pass

    def logout(self):
        pass

    def get_album(self, album_id):
        pass
