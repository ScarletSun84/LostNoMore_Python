import http.server
import socketserver
import webbrowser
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8000
APP_DIR = Path(__file__).resolve().parent

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[LostNoMore] {self.address_string()} - {format % args}")

def main():
    # Serve the LostNoMore HTML/CSS/JS/image files from this folder.
    import os
    os.chdir(APP_DIR)

    with socketserver.TCPServer((HOST, PORT), QuietHandler) as server:
        url = f"http://{HOST}:{PORT}/index.html"
        print("=" * 60)
        print("LostNoMore is running!")
        print(f"Open: {url}")
        print("Press CTRL+C in this window to stop the server.")
        print("=" * 60)

        webbrowser.open(url)

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nLostNoMore stopped.")

if __name__ == "__main__":
    main()
