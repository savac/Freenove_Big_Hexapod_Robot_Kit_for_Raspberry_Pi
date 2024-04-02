import threading
from Server import Server


if __name__ == '__main__':
        server=Server()
        server.turn_on_server()
        server.tcp_flag=True
        video=threading.Thread(target=server.transmission_video)
        video.start()
        instruction=threading.Thread(target=server.receive_instruction)
        instruction.start()
