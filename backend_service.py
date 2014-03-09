import threading
import queue
import spotify

class ControllerThread(threading.Thread):

    def __init__(self, out_queue):
        self.in_queue = queue.Queue()
        self.out_queue = out_queue
        self.session = spotify.Session()
        self.active = True
        self.register_callbacks()

    def run(self):
        while self.active:
            self.execute_command()
                
    def execute_command(self):
        valid_opcodes = ('login', 'logout', 'get_album', 'get_song', 'exit',
                         'process_events')
        try:
            command = self.in_queue.get_nowait()
            if command.opcode in valid_opcodes:
                getattr(self, command.opcode)(*command.args)
        except queue.Empty:
            pass

    def login(self, username, password): 
        pass 

    def logout(self):
        pass

    def get_album(self, album_id):
        pass

    def get_song(self, song_id):
        pass

    def exit(self):
        self.active = False

    def process_events(self):
        self.session.process_events()

    def login_complete(self):
        pass

    def logout_complete(self):
        pass

    def trigger_callbacks(self):
        ''' This is a callback that is called by an internal libspotify thread
            to notify this thread that it should process all other pending 
            events, hence the somewhat strange behaviour of this object sending
            a command to itself. '''
        command = Command('process_events')
        self.in_queue.put_nowait(command)

    def register_callbacks(self):
        callbacks = {
            'LOGGED_IN': self.login_complete,
            'LOGGED_OUT': self.logout_complete,
            'NOTIFY_MAIN_THREAD': self.trigger_callbacks
        }
        for name in callbacks:
            self.session.on(getattr(spotify.SessionEvent, name), callbacks[name])


class Command:

    def __init__(self, input_string):
        tokens = input_string.split(' ')
        self.opcode = tokens[0]
        self.args = tokens[1:]
