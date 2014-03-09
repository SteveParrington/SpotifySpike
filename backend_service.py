import threading
import Queue
import spotify

class ControllerThread(threading.Thread):

    def __init__(self, out_queue):
        self.in_queue = Queue.Queue()
        self.out_queue = out_queue
        self.session = spotify.Session()
        self.active = True
        self.register_callbacks()
        super(ControllerThread, self).__init__()

    def run(self):
        while self.active:
            self.execute_command()
            self.session.process_events()

    def execute_command(self):
        valid_opcodes = ('login', 'logout', 'get_album', 'get_song', 'exit',
                         'process_events')
        try:
            command = self.in_queue.get_nowait()
            if command.opcode in valid_opcodes:
                getattr(self, command.opcode)(*command.args)
        except Queue.Empty:
            pass

    def login(self, username, password): 
        self.session.login(username, password) 

    def logout(self):
        self.session.logout() 

    def get_album(self, album_id):
        pass

    def get_song(self, song_id):
        pass

    def exit(self):
        self.active = False

    def login_complete(self, session, error_type):
        self.out_queue.put_nowait("Login successful!")

    def logout_complete(self, session):
        self.out_queue.put_nowait("Logged out")

    def register_callbacks(self):
        callbacks = {
            'LOGGED_IN': self.login_complete,
            'LOGGED_OUT': self.logout_complete
        }
        for name in callbacks:
            print(getattr(spotify.SessionEvent, name))
            self.session.on(getattr(spotify.SessionEvent, name), callbacks[name])


class Command:

    def __init__(self, input_string):
        tokens = input_string.split(' ')
        self.opcode = tokens[0]
        self.args = tokens[1:]
