import threading
from config import HOST, PORT
from net.tcp_client import TCPClient
from core.controller import Controller
from ui.app import App


# Entry point of program

def main():
    # setup controller and client objects
    client = TCPClient(HOST, PORT)
    controller = Controller(client)

    # start seperate thread for connection
    net_thread = threading.Thread(target=controller.run, daemon=True)
    net_thread.start()

    # launch app
    app = App(controller)
    app.mainloop()

if __name__ == "__main__":
    main()