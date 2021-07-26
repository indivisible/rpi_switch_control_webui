#!/usr/bin/env python3

import asyncio
import subprocess
import logging

from controller_common import button_mappings, stick_mappings
from scripting import Script


class Controller:
    def __init__(self, stream, manager):
        self.command_stream = stream
        self.manager = manager

    async def __write_line(self, *words):
        line = ' '.join(words) + '\n'
        self.command_stream.write(line.encode('ascii'))
        await self.command_stream.drain()

    async def press(self, button):
        await self.__write_line(button_mappings[button], '1')

    async def release(self, button):
        await self.__write_line(button_mappings[button], '0')

    async def release_all(self):
        for name in button_mappings.keys():
            await self.release(name)

    async def reset_inputs(self):
        await self.release_all()
        await self.move_stick(0, 0, 0)
        await self.move_stick(1, 0, 0)

    async def move_stick(self, idx, x, y):
        stick = stick_mappings[idx]
        await self.__write_line(stick[0], str(x))
        await self.__write_line(stick[1], str(y))


class BackendManager:
    abort_buttons = ['A', 'B', 'X', 'Y', '+', '-', 'Home']

    def __init__(self, command='/bin/cat', args=[]):
        self.command = command
        self.command_args = args
        self.socket_send_message = None
        self.proc = None
        self.controller = None
        self.script_task = None
        self.script_abort = asyncio.Event()
        self.script_abort.set()

    async def send_message(self, severity, message):
        if self.socket_send_message is None:
            return
        await self.socket_send_message(severity, message)

    async def start(self):
        self.proc = await asyncio.create_subprocess_exec(
            self.command, *self.command_args, stdin=subprocess.PIPE)
        self.controller = Controller(self.proc.stdin, self)

    def start_script(self, script_text: str):
        script = Script(script_text)
        self.script_task = asyncio.create_task(self.__run_script(script))

    async def __run_script(self, script: Script):
        # 1st stop the running script
        self.script_abort.set()
        script_abort = asyncio.Event()
        self.script_abort = script_abort
        controller_ops = set([
                'release_all',
                'reset_inputs',
                'press',
                'release',
                'move_stick',
                ])

        for op in script:
            if script_abort.is_set():
                break
            print(op)
            if op.name == 'wait':
                await asyncio.sleep(op.args[0] / 1000)
            elif op.name == 'message':
                await self.send_message('info', op.args[0])
            elif op.name in controller_ops:
                fun = getattr(self.controller, op.name)
                await fun(*op.args)
            else:
                await self.send_message('error', f'Unkown OP: {op}')
                logging.error(f'unkown OP: {op}')
        await self.send_message('info', 'Script finished.')

    def abort_script(self):
        self.script_abort.set()

    async def manual_input(self, input_state):
        if not self.script_abort.is_set():
            for button in self.abort_buttons:
                if input_state[button]:
                    self.script_abort.set()
                    break
            else:
                # no button pressed, macro can continue
                return
        # TODO
