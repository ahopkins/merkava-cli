from prompt_toolkit import prompt
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.contrib.completers import WordCompleter
import msgpack
import trio
import sys
from time import sleep


# import sys

# # arbitrary, but:
# # - must be in between 1024 and 65535
# # - can't be in use by some other program on your computer
# # - must match what we set in our echo server
# PORT = 12345
# # How much memory to spend (at most) on each call to recv. Pretty arbitrary,
# # but shouldn't be too big or too small.
# BUFSIZE = 16384

# async def sender(client_stream):
#     print("sender: started!")
#     while True:
#         data = b"async can sometimes be confusing, but I believe in you!"
#         print("sender: sending {!r}".format(data))
#         await client_stream.send_all(data)
#         await trio.sleep(1)

# async def receiver(client_stream):
#     print("receiver: started!")
#     while True:
#         data = await client_stream.receive_some(BUFSIZE)
#         print("receiver: got data {!r}".format(data))
#         if not data:
#             print("receiver: connection closed")
#             sys.exit()

# async def parent():
#     print("parent: connecting to 127.0.0.1:{}".format(PORT))
#     client_stream = await trio.open_tcp_stream("127.0.0.1", PORT)
#     async with client_stream:
#         async with trio.open_nursery() as nursery:
#             print("parent: spawning sender...")
#             nursery.start_soon(sender, client_stream)

#             print("parent: spawning receiver...")
#             nursery.start_soon(receiver, client_stream)

# trio.run(parent)


trigger_commands = ['CONNECT', 'STATS',
                    'PUSH', 'RETRIEVE', 'UPDATE', 'RECENT',
                    'DELETE', 'RESTORE', 'PURGE',
                    'CLEAN', 'FLUSH', 'HELP']
history = InMemoryHistory()
completer = WordCompleter([f'{x} ' for x in trigger_commands],
                          ignore_case=True, sentence=True)
host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
port = sys.argv[2] if len(sys.argv) > 2 else 6363
# channel = None
channel = 'foo'
BUFSIZE = 16384


logo = """

     +-----------------+
     |    Welcome to   |
     +-----------------+
     |    MerkavaDB    |
     +-----------------+

"""


# class Connection:
#     def __enter__(self):
#         global host
#         global port

#         try:
#             self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         except socket.error as e:
#             print('Unable to instantiate socket. Error code: ' +
#                   str(e[0]) + ' , Error message : ' + e[1])

#         self.sock.connect((host, port))
#         return self

#     def __exit__(self, *args, **kwargs):
#         self.sock.close()

#     def send(self, msg):
#         self.sock.send(msg)


def get_input_prompt(channel):
    if channel is None:
        display = 'no connected channel'
    else:
        display = channel
    return f'{display.upper()}> '


async def send(client_stream, command, payload):
    # msg = msgpack.packb({
    #     'command': command,
    #     'channel': channel,
    #     'payload': payload
    # })
    msg = bytes(f'{channel} {command} {payload}', 'utf-8')
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
        print(f'\n{packet}\n')
        await trio.sleep(0.1)


async def process():
    print(f"connecting to {host}:{port}")
    client_stream = await trio.open_tcp_stream(host, port)
    async with client_stream:
        async with trio.open_nursery() as nursery:
            nursery.start_soon(sender, client_stream)
            nursery.start_soon(receiver, client_stream)


def main():
    print(logo)

    try:
        # with Connection() as connection:
        #     while True:
        #         text = prompt(get_input_prompt(channel), history=history,
        #                       completer=completer,
        #                       bottom_toolbar='Connected to {host}:{port}'.format(host=host, port=port))
        #         handle(connection, text)
        trio.run(process)
    except KeyboardInterrupt:
        print('shutting down')
    except trio.BrokenStreamError:
        print('BrokenStreamError')
        sleep(3)
        print('retrying')
        trio.run(process)
    finally:
        print('GoodBye!')


if __name__ == '__main__':
    main()
