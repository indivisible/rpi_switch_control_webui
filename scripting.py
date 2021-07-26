#!/usr/bin/env python3

from collections import defaultdict

sample_script = '''
macro exit:
    press B
    wait 100
    release B
end
# lines starting with # are comments
# no in-line comments allowed following statements!

press B
wait 500
release_all
wait 1000

repeat 3:
    press A

    wait 300
    release_all
    repeat 2:
        call exit
    end
end

# comment!
release_all
#repeat 0:
#end
'''

# FIXME: duplicated constants!
VALID_BUTTONS = set([
    'A', 'B', 'X', 'Y',
    'L', 'R', 'ZL', 'ZR',
    '+', '-', 'Home', 'Capture',
    'LS', 'RS'
    ])


class ScriptEOF(Exception):
    pass


class SimpleOp:
    is_simple = True
    is_block = False

    def __init__(self, args, *_):
        self.args = self.init_args(args)

    def init_args(self, args):
        raise Exception('not implemented')

    def __iter__(self):
        yield self

    def __repr__(self):
        return f'<{self.name} {self.args}>'


class NoArgsOp(SimpleOp):
    def init_args(self, args):
        if args:
            raise ValueError(f'{self.name} does not take arguments')
        return []


class PressOp(SimpleOp):
    name = 'press'

    def init_args(self, args):
        (button,) = args
        if button not in VALID_BUTTONS:
            raise ValueError(f'invalid button name {button}')
        return [button]


class ReleaseOp(PressOp):
    name = 'release'


class MoveStickOp(SimpleOp):
    name = 'move_stick'

    def init_args(self, args):
        if len(args) != 3:
            raise ValueError('move_stick takes 3 arguments!')

        def ranged_float(raw, min, max):
            val = float(raw)
            if not min <= val <= max:
                raise ValueError(f'value {val} out of range {min} {max}')
            return val

        idx = int(args[0])
        if not 0 <= idx <= 1:
            raise ValueError(f'Unkown axis {args[0]}')
        x = ranged_float(args[1], -1, 1)
        y = ranged_float(args[2], -1, 1)
        return [idx, x, y]


class ReleaseAllOp(NoArgsOp):
    name = 'release_all'


class ResetInputsOp(NoArgsOp):
    name = 'reset_inputs'


class WaitOp(SimpleOp):
    name = 'wait'

    def init_args(self, args):
        (time,) = args
        time = int(time)
        if not time > 0:
            raise ValueError(f'invalid number of milliseconds: {time}')
        return [time]


class MessageOp(SimpleOp):
    name = 'message'

    def init_args(self, args):
        message = ' '.join(args)
        return [message]


class TapOp:
    name = 'tap'
    is_simple = True
    is_block = False

    def __init__(self, args, *_):
        self.ops = []
        hold = '100'
        wait = '100'

        if not 1 <= len(args) <= 3:
            raise ValueError(f'expected 1-3 args, got {args!r}')

        if len(args) >= 2:
            hold = args[1]
        if len(args) >= 3:
            wait = args[2]
            if int(wait) == 0:
                wait = None

        self.ops.append(PressOp([args[0]]))
        self.ops.append(WaitOp([hold]))
        self.ops.append(ReleaseOp([args[0]]))
        if wait:
            self.ops.append(WaitOp([wait]))

    def __iter__(self):
        yield from self.ops


class MacroOp:
    name = 'macro'
    is_simple = False

    def __init__(self, args, parents, script):
        if parents:
            raise ValueError('macros must be top defined at top level')
        (arg,) = args
        if not arg[-1] == ':':
            raise ValueError('missing colon in macro definition')
        label = arg[:-1].strip()
        if not label:
            raise ValueError(f'invalid label {arg!r}')
        if label in script.macros:
            raise ValueError(f'duplicate macro name {label!r}')
        self.label = label
        self.is_block = True
        self.children = []
        script.macros[self.label] = self

    def __iter__(self):
        # nothing is executed unless we get called
        return
        yield

    def call(self):
        for child in self.children:
            yield from child


class RepeatOp:
    name = 'repeat'
    is_simple = False

    def __init__(self, args, parents, script):
        arg, *rest = args
        self.message = rest
        if not arg[-1] == ':':
            raise ValueError('missing colon in loop statement')
        count = arg[:-1].strip()
        if not count:
            raise ValueError(f'invalid repeat count {arg!r}')
        count = int(count)
        self.count = count
        self.is_block = True
        self.children = []

    def __iter__(self):
        if self.count <= 0:
            # infinite loop
            loop = iter(int, 1)
        else:
            loop = range(self.count)
        for i in loop:
            if self.message:
                msg = [f'{i+1}/{self.count}:'] + self.message
                yield from MessageOp(msg)
            for child in self.children:
                yield from child


class EndOp:
    name = 'end'
    is_simple = False
    is_block = False

    def __init__(self, args, context, *_):
        if not context:
            raise ValueError('too many end statements')
        if args:
            raise ValueError('`end` does not accept arguments')


class CallOp:
    name = 'call'
    is_block = False
    is_simple = False

    def __init__(self, args, context, script):
        self.script = script
        (arg,) = args
        label = arg.strip()
        if not label:
            raise ValueError(f'invalid macro name {arg}')
        self.label = label
        script.called_macros.add(label)

    def __iter__(self):
        yield from self.script.macros[self.label].call()


op_types_list = [
        PressOp,
        ReleaseOp,
        ReleaseAllOp,
        MoveStickOp,
        ResetInputsOp,
        WaitOp,
        MessageOp,
        TapOp,
        MacroOp,
        RepeatOp,
        EndOp,
        CallOp,
    ]

op_types = dict((cls.name, cls) for cls in op_types_list)


class ScriptTokenizer:
    def __init__(self, text, script):
        self.lines = text.split('\n')
        self.pos = 0
        self.script = script

    def get_line(self):
        while True:
            if self.pos >= len(self.lines):
                return None
            line = self.lines[self.pos].strip()
            pos = self.pos
            self.pos += 1
            if not line:
                continue
            if line[0] == '#':
                continue
            return (pos, line)

    def get_block(self, parents):
        statements = []
        while True:
            statement = self.get_statement(parents)
            if statement is None:
                if parents:
                    raise SyntaxError('too few `end` statements')
                return statements
            if statement.name == 'end':
                return statements
            statements.append(statement)
        return statements

    def get_statement(self, parents):
        pos_line = self.get_line()
        if pos_line is None:
            return None
        pos, line = pos_line
        op_name, *args = line.split()

        op = op_types[op_name](args, parents, self.script)
        if op.is_block:
            op.children = self.get_block(parents + [op.name])
        return op


class Script:
    def __init__(self, text):
        self.macros = dict()
        self.called_macros = set()
        tokenizer = ScriptTokenizer(text, self)
        self.ops = tokenizer.get_block([])

        self.validate()

    def validate(self):
        '''validate that the script can not cause a hang, or runtime errors'''

        # check invalid calls
        for name in self.called_macros:
            if name not in self.macros:
                raise SyntaxError(f'unkown macro {name}')

        # check for recursion (cycles in the call graph)
        self.check_cycles()

        # check for macros and loops not emitting any instructions
        self.check_empty(self.ops)

    def check_empty(self, ops):
        empty = True
        for op in ops:
            if op.is_simple or op.name == 'call':
                empty = False
            elif op.name == 'macro':
                self.check_empty(op.children)
            elif op.name == 'repeat':
                self.check_empty(op.children)
                empty = False
        if empty:
            raise SyntaxError('block does not emit any instructions')

    def check_cycles(self):
        colors = defaultdict(int)
        calls = defaultdict(set)

        # build a call graph
        for name, macro in self.macros.items():
            for op in macro.children:
                if op.name == 'call':
                    calls[name].add(op.label)

        # graph coloring cycle finder
        # 0: unvisited, 1: in progress, 2: done
        def color_check(name):
            colors[name] = 1
            for call in calls[name]:
                if colors[call] == 1:
                    return True
                if colors[call] == 0 and color_check(call):
                    return True
            colors[name] = 2
            return False

        for name in self.macros.keys():
            if colors[name] == 0 and color_check(name):
                raise SyntaxError('recursion is not allowed!')

    def __iter__(self):
        for top_level_op in self.ops:
            yield from top_level_op


if __name__ == '__main__':
    s = Script(sample_script)
    print(s)
    for op in s:
        print(f'{op}')
