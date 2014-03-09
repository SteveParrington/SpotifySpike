from backend_service import ControllerThread, Command
import Queue

def enter_repl(request_queue, reply_queue):
    print("SpotifySpike - Developed by Steve Parrington")
    try:
        while True:
            text_command = raw_input("> ")
            command = Command(text_command)
            if text_command == 'exit':
                raise KeyboardInterrupt 
            request_queue.put(command)
            print(reply_queue.get())
    except KeyboardInterrupt:
        print("Exiting SpotifySpike...")
        request_queue.put(Command('logout'))
        reply_queue.get()
        request_queue.put(Command('exit'))

def main():
    reply_queue = Queue.Queue()
    controller = ControllerThread(reply_queue)
    request_queue = controller.in_queue
    controller.start()
    enter_repl(request_queue, reply_queue)

if __name__ == '__main__':
    main()
