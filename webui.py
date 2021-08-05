#!/usr/bin/env python3

import logging
import asyncio
import threading
import json
from http.server import HTTPServer, SimpleHTTPRequestHandler
from functools import partial
from pathlib import Path

import websockets

from backend_manager import BackendManager


class SocketConnection:
    def __init__(self, socket, backend: BackendManager):
        self.socket = socket
        self.backend = backend

    async def send(self, obj):
        return await self.socket.send(json.dumps(obj))

    async def send_message(self, severity: str, message):
        return await self.send(self.message(severity, message))

    def action(self, action: str, **rest):
        rest['action'] = action
        return rest

    def message(self, severity: str, message):
        return self.action(
                'message', severity=severity, message=message)

    def error(self, msg):
        return self.message('error', message=msg)

    async def handle_message(self, raw: str):
        data = json.loads(raw)
        action = data.pop('action').replace('-', '_')
        try:
            handler = getattr(self, f'handle_action_{action}')
        except AttributeError:
            return self.error(f'Unkown action f{action}')
        try:
            reply = await handler(**data)
            return reply
        except Exception as e:
            logging.exception(f'Error handling {action}:')
            return self.error(f'Error handling {action}: {e}')

    async def serve(self):
        async for message in self.socket:
            try:
                reply = await self.handle_message(message)
            except Exception:
                logging.error(f'Error handling message {message}: ')
                reply = self.error('Invalid message')

            if reply is not None:
                await self.send(reply)

    async def handle_action_status(self):
        # return self.action('status', ok=(con is not None))
        return self.action('status', ok=True)

    async def handle_action_run_script(self, text):
        if not text:
            return self.error('empty script')
        else:
            try:
                self.backend.start_script(text)
                return self.message('info', 'script started')
            except Exception as e:
                logging.exception('Error running script:')
                return self.error(f'error running script: {e!r}')

    async def handle_action_abort_script(self):
        self.backend.abort_script()
        return self.message('warning', 'Script aborted')

    async def handle_action_restart(self):
        Path('restart_app').touch()
        return self.error('Restarting app')


class SocketServer:
    def __init__(self, backend):
        self.backend = backend
        backend.socket_send_message = self.send_message
        self.connections = []

    async def send_message(self, severity: str, message):
        for con in self.connections:
            try:
                await con.send_message(severity, message)
            except Exception:
                logging.exception('error sending message to websocket')

    async def serve(self, websocket, path):
        connection = SocketConnection(websocket, self.backend)
        self.connections.append(connection)
        try:
            await connection.serve()
        finally:
            self.connections.remove(connection)


async def start_websocket_server(backend):
    await backend.start()
    server = SocketServer(backend)
    await websockets.serve(server.serve, "0.0.0.0", 6789)
    logging.debug('started websocket server')


def run_http_server(path):
    server_address = ('', 8000)
    handler = partial(SimpleHTTPRequestHandler, directory=path)
    httpd = HTTPServer(server_address, handler)
    logging.debug('starting HTTP server')
    httpd.serve_forever()


def main():
    import argparse

    parser = argparse.ArgumentParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('cmd', default=['/bin/cat'], nargs='*')

    args = parser.parse_args()

    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger('websockets.protocol').setLevel(logging.WARNING)
    logging.getLogger('websockets.server').setLevel(logging.WARNING)

    cmd, *cmd_args = args.cmd
    backend = BackendManager(cmd, cmd_args)

    # http server for static files of the GUI
    httpd_thread = threading.Thread(
            target=run_http_server,
            # the directory where the served files are
            args=('html',),
            daemon=True)
    httpd_thread.start()

    # websocket for client controls
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_websocket_server(backend))
    loop.run_forever()

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
