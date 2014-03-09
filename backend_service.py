import threading
import Queue
import spotify
import alsaaudio

class BufferThread(threading.Thread):

    def __init__(self):
        self.in_queue = Queue.Queue()
        self.pcm = alsaaudio.PCM(type=alsaaudio.PCM_PLAYBACK, mode=alsaaudio.PCM_NORMAL)
        self.pcm.setchannels(2)
        self.pcm.setrate(44100)
        self.pcm.setformat(alsaaudio.PCM_FORMAT_S16_LE)
        self.pcm.setperiodsize(2048)
        self.active = True
        super(BufferThread, self).__init__()

    def run(self):
        while self.active:
            data = self.in_queue.get() 
            self.pcm.write(data)

class ControllerThread(threading.Thread):

    def __init__(self, out_queue):
        self.in_queue = Queue.Queue()
        self.out_queue = out_queue
        self.session = spotify.Session()
        self.active = True
        self.register_callbacks()
        self.buffer_thread = BufferThread()
        self.buffer_queue = self.buffer_thread.in_queue
        self.buffer_thread.start()
        self.current_song = None
        super(ControllerThread, self).__init__()

    def run(self):
        while self.active:
            self.execute_command()
            self.session.process_events()

    def execute_command(self):
        valid_opcodes = ('login', 'logout', 'get_album', 'get_song', 'exit',
                         'play')
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
        album = spotify.Album('spotify:album:{0}'.format(album_id))
        album.load()
        response = "Title: {0}\nArtist: {1}".format(album.name, album.artist.name)
        self.out_queue.put(response)

    def get_song(self, song_id):
        song = spotify.Track('spotify:track:{0}'.format(song_id))
        song.load()
        self.current_song = song
        response = "Title: {0}\nArtist: {1}".format(song.name, song.album.artist.name)
        self.out_queue.put(response)

    def exit(self):
        self.active = False

    def play(self):
        if self.current_song is not None:
            player = self.session.player
            player.load(self.current_song)
            player.play()
            self.out_queue.put('Playing {0}'.format(self.current_song.name))
        self.out_queue.put('No song loaded')

    def login_complete(self, session, error_type):
        self.out_queue.put_nowait("Login successful!")

    def logout_complete(self, session):
        self.out_queue.put_nowait("Logged out")

    def music_delivery(self, session, audio_format, frames, num_frames):
        self.buffer_queue.put(frames)
        return num_frames

    def register_callbacks(self):
        callbacks = {
            'LOGGED_IN': self.login_complete,
            'LOGGED_OUT': self.logout_complete,
            'MUSIC_DELIVERY': self.music_delivery
        }
        for name in callbacks:
            self.session.on(getattr(spotify.SessionEvent, name), callbacks[name])


class Command:

    def __init__(self, input_string):
        tokens = input_string.split(' ')
        self.opcode = tokens[0]
        self.args = tokens[1:]
