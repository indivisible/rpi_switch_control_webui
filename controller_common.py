#!/usr/bin/env python3

button_mappings = {
        'A': 'a',
        'B': 'b',
        'X': 'x',
        'Y': 'y',

        '+': 'p',
        '-': 'm',
        'Home': 'h',
        'Capture': 'c',

        'R': 'r1',
        'L': 'l1',
        'ZR': 'r2',
        'ZL': 'l2',

        'LS': 'lp',
        'RS': 'rp',

        'Up': 'pu',
        'Right': 'pr',
        'Down': 'pd',
        'Left': 'pl',
        }

buttons = set(button_mappings.keys())

stick_mappings = [
        ['lx', 'ly'],
        ['rx', 'ry']
        ]
