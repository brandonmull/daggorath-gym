import config
import funcs
import subprocess
import socket

server_socket = funcs.open_socket()

process = subprocess.Popen(
    config.cmd,
    shell=False,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

