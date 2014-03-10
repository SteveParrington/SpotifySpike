import threading
import Queue
import spotify
import alsaaudio

class AudioError(Exception):
    pass


class AudioQueue(Queue.Queue):
    ''' Made to enable a queue used for audio to be cleared when necessary, it also
        disables threads from trying to put new data into the queue while it is 
        being cleared '''

    def __init__(self):
        self.allow_put = True
        # Queue is an old style object so we need to do old style inheritance
        # Boo Python 2!
        Queue.Queue.__init__(self)

    def put(self, *args):
        if self.allow_put:
            Queue.Queue.put(self, *args)
        else:
            raise AudioError('CustomQueue.put was attempted while the queue was clearing')

    def clear(self):
        self.allow_put = False
        try:
            while True:
                self.get_nowait()
        except Queue.Empty:
            self.allow_put = True


class AudioThread(threading.Thread):

    def __init__(self):
        self.audio_queue = AudioQueue()
        self.command_queue = Queue.Queue()
        self.play_audio = True
        self.pcm = alsaaudio.PCM(type=alsaaudio.PCM_PLAYBACK, mode=alsaaudio.PCM_NORMAL)
        self.pcm.setchannels(2)
        self.pcm.setrate(44100)
        self.pcm.setformat(alsaaudio.PCM_FORMAT_S16_LE)
        self.pcm.setperiodsize(2048)
        self.active = True
        super(AudioThread, self).__init__()

    def run(self):
        while self.active:
            self.process_audio()
            self.execute_command()

    def process_audio(self):
        try:
            if self.play_audio:
                data = self.audio_queue.get_nowait()
                self.pcm.write(data)
        except Queue.Empty:
            pass

    def execute_command(self):
        valid_opcodes = ('play', 'pause', 'clear_audio', 'exit')
        try:
            command = self.command_queue.get_nowait()
            if command.opcode in valid_opcodes:
                getattr(self, command.opcode)()
        except Queue.Empty:
            pass

    def play(self):
        self.play_audio = True

    def pause(self):
        self.play_audio = False

    def clear_audio(self):
        self.audio_queue.clear()

    def exit(self):
        self.active = False


class ControllerThread(threading.Thread):

    def __init__(self, out_queue):
        self.in_queue = Queue.Queue()
        self.out_queue = out_queue
        self.session = spotify.Session()
        self.active = True
        self.register_callbacks()
        self.audio_thread = AudioThread()
        self.audio_queue = self.audio_thread.audio_queue
        self.audio_command_queue = self.audio_thread.command_queue
        self.audio_thread.start()
        self.next_song = None
        self.current_song = None
        super(ControllerThread, self).__init__()

    def run(self):
        while self.active:
            self.execute_command()
            self.session.process_events()

    def execute_command(self):
        valid_opcodes = ('login', 'logout', 'get_album', 'get_song', 'exit',
                         'play', 'pause')
        try:
            command = self.in_queue.get_nowait()
            if command.opcode in valid_opcodes:
                getattr(self, command.opcode)(*command.args)
            else:
                self.out_queue.put('Invalid command, try again')
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
        self.next_song = song
        response = "Title: {0}\nArtist: {1}".format(song.name, song.album.artist.name)
        self.out_queue.put(response)

    def exit(self):
        self.active = False
        self.audio_command_queue.put(Command('exit'))

    def play(self):
        if self.next_song is not None and self.current_song is None:
            player = self.session.player
            self.current_song = self.next_song
            self.next_song = None
            player.load(self.current_song)
            player.play()
            self.out_queue.put('Playing {0}'.format(self.current_song.name))
        elif self.current_song is not None:
            self.session.player.play()
            self.audio_command_queue.put(Command('play'))
            self.out_queue.put('Playing {0}'.format(self.current_song.name))
        else:
            self.out_queue.put('No song loaded')

    def pause(self):
        if self.current_song is not None:
            self.session.player.play(False)
            self.audio_command_queue.put(Command('pause'))
            self.out_queue.put('Paused {0}'.format(self.current_song.name))
        else:
            self.out_queue.put('Not currently playing anything!')

    def login_complete(self, session, error_type):
        self.out_queue.put_nowait("Login successful!")

    def logout_complete(self, session):
        self.out_queue.put_nowait("Logged out")

    def music_delivery(self, session, audio_format, frames, num_frames):
        self.audio_queue.put(frames)
        return num_frames

    def end_of_track(self, session):
        self.session.player.unload()
        self.current_song = None

    def register_callbacks(self):
        callbacks = {
            'LOGGED_IN': self.login_complete,
            'LOGGED_OUT': self.logout_complete,
            'MUSIC_DELIVERY': self.music_delivery,
            'END_OF_TRACK': self.end_of_track
        }
        for name in callbacks:
            self.session.on(getattr(spotify.SessionEvent, name), callbacks[name])


class Command:

    def __init__(self, input_string):
        tokens = input_string.split(' ')
        self.opcode = tokens[0]
        self.args = tokens[1:]
