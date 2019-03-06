from prompt_toolkit import prompt
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.contrib.completers import WordCompleter
from prompt_toolkit import print_formatted_text as printf, HTML, ANSI
from pygments import highlight
from pygments.lexers import JsonLexer
from pygments.formatters import TerminalFormatter
import trio
import sys
import json
from time import sleep


trigger_commands = ['CONNECT', 'STATS',
                    'PUSH', 'RETRIEVE', 'UPDATE', 'RECENT',
                    'DELETE', 'RESTORE', 'PURGE',
                    'BACKUP', 'CLEAN', 'FLUSH',
                    'HELP']
history = InMemoryHistory()
completer = WordCompleter([f'{x} ' for x in trigger_commands],
                          ignore_case=True, sentence=True)
host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
port = sys.argv[2] if len(sys.argv) > 2 else 6363

channel = 'foo'
BUFSIZE = 16384


logo = """

     +-----------------+
     |    Welcome to   |
     +-----------------+
     |    MerkavaDB    |
     +-----------------+

"""


def get_input_prompt(channel):
    if channel is None:
        display = 'no connected channel'
    else:
        display = channel
    return f'{display.upper()}> '


def parse_packet(packet):
    status, message = packet.decode().split(' ', 1)

    try:
        return status, json.dumps(json.loads(message), indent=4, sort_keys=True), True
    except json.decoder.JSONDecodeError:
        return status, message, False


async def send(client_stream, command, payload):
    msg = bytes(f'{channel} {command} {payload}\n', 'utf-8')
    await client_stream.send_all(msg)


async def handle(client_stream, incoming):
    global channel

    incoming = incoming.split(' ')
    command = incoming[0].upper()
    payload = ' '.join(incoming[1:])

    if command == 'HELP':
        print(trigger_commands)
        return
    elif command == 'CONNECT':
        channel = incoming[1]

    if channel is not None:
        if command in trigger_commands:
            await send(client_stream, command, payload)
        else:
            print('Unknown command')
    else:
        print('You must connect to a channel first')


async def sender(client_stream):
    while True:
        text = prompt(get_input_prompt(channel), history=history,
                      completer=completer,
                      bottom_toolbar='Connected to {host}:{port}'.format(host=host, port=port))
        await handle(client_stream, text)
        await trio.sleep(0.1)


async def receiver(client_stream):
    while True:
        packet = await client_stream.receive_some(BUFSIZE)
        # data = msgpack.unpackb(packet, use_list=False, raw=False)
        status, message, as_json = parse_packet(packet)

        color = "ansigreen" if status == "OK" else "ansired"
        printf(HTML(f"\n>>\t<{color}><b>{status}</b></{color}>"))

        if as_json:
            message = highlight(message, JsonLexer(), TerminalFormatter())
        printf(ANSI('\t' + message.replace("\n", "\n\t")))

        await trio.sleep(0.1)


async def process():
    printf(HTML(f"<ansiwhite>connecting to <b>{host}:{port}</b></ansiwhite>\n"))
    client_stream = await trio.open_tcp_stream(host, port)
    async with client_stream:
        async with trio.open_nursery() as nursery:
            nursery.start_soon(sender, client_stream)
            nursery.start_soon(receiver, client_stream)


def main():
    print(logo)

    try:
        trio.run(process)
    except KeyboardInterrupt:
        print('\nshutting down')
    except trio.BrokenStreamError:
        print('BrokenStreamError')
        sleep(3)
        print('retrying')
        trio.run(process)
    finally:
        print('GoodBye!\n')


if __name__ == '__main__':
    main()
