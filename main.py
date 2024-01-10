from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver
import urllib.parse
import mimetypes
import pathlib
import socket
import json
from datetime import datetime
import threading


HTTP_SERVER_PORT = 3000
HTTP_SERVER_ADDRESS = ("0.0.0.0", HTTP_SERVER_PORT)

SOCKET_SERVER_PORT = 5000
SOCKET_SERVER_ADDRESS = ("0.0.0.0", SOCKET_SERVER_PORT)

SERVER_SOCKET_IP = "127.0.0.1"
DATA_JSON_FILE_PATH = "storage/data.json"


def send_to_socket_server(data):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(data, (SERVER_SOCKET_IP, SOCKET_SERVER_PORT))


class MySocketHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = self.request[0].strip()
        addr = self.client_address
        print(f"Received data from {addr}: {data}")

        # Parse and save data to data.json
        save_to_json(data)


class MyHttpRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        data = self.rfile.read(int(self.headers["Content-Length"]))

        send_to_socket_server(data)
        self.send_response(302)
        self.send_header("Location", "/")
        self.end_headers()

    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
        if pr_url.path == "/":
            self.send_html_file("index.html")
        elif pr_url.path == "/message":
            self.send_html_file("message.html")
        else:
            if pathlib.Path().joinpath(pr_url.path[1:]).exists():
                self.send_static()
            else:
                self.send_html_file("error.html", 404)

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        with open(filename, "rb") as fd:
            self.wfile.write(fd.read())

    def send_static(self):
        self.send_response(200)
        mt = mimetypes.guess_type(self.path)
        if mt:
            self.send_header("Content-type", mt[0])
        else:
            self.send_header("Content-type", "text/plain")
        self.end_headers()
        with open(f".{self.path}", "rb") as file:
            self.wfile.write(file.read())


def run_http_server():
    with socketserver.TCPServer(
        HTTP_SERVER_ADDRESS, MyHttpRequestHandler
    ) as http_server:
        print(f"HTTP Server is running on http://localhost:{HTTP_SERVER_PORT}")
        http_server.serve_forever()


def run_socket_server():
    with socketserver.UDPServer(
        SOCKET_SERVER_ADDRESS, MySocketHandler
    ) as socket_server:
        print(f"Socket Server is running on udp://localhost:{SOCKET_SERVER_PORT}")
        socket_server.serve_forever()


from urllib.parse import parse_qs


def save_to_json(data):
    try:
        parsed_data = parse_qs(data.decode())
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        data_dict = {
            timestamp: {
                "username": parsed_data["username"][0],
                "message": parsed_data["message"][0],
            }
        }
        with open(DATA_JSON_FILE_PATH, "r+") as json_file:
            try:
                existing_data = json.load(json_file)
            except json.JSONDecodeError:
                existing_data = {}

            existing_data.update(data_dict)

            json_file.seek(0)
            json.dump(existing_data, json_file, indent=2)
            json_file.truncate()
    except Exception as e:
        print(f"Error saving to JSON: {e}")


if __name__ == "__main__":
    http_thread = threading.Thread(target=run_http_server)
    socket_thread = threading.Thread(target=run_socket_server)

    http_thread.start()
    socket_thread.start()

    http_thread.join()
    socket_thread.join()
