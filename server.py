import os
import time
import _thread
from _thread import *
import socket
from socket import *
import struct
from struct import *

list_lock = _thread.allocate_lock()
user_list = {}
hallway = {}
file_transfer_keys = {}
port_map = {}

port_h = 2050


def initializer(handler_socket, port_h):
    connection_h, address_h = handler_socket.accept()
    connection_h.send(b'\nWelcome to Internet Relay Chat')
    status = 'unregistered'
    global port_m
    while status == 'unregistered':
        try:
            command = connection_h.recv(32).decode('ascii')
        except ConnectionError:
            #	except OSError:
            _thread.exit()
        else:
            [intent, argument] = command.split(' ')
            if intent == 'register':
                list_lock.acquire()
                if argument not in user_list:
                    user_list[argument] = port_m
                    list_lock.release()
                    port_map[port_m] = argument
                    status = 'registered'
                    connection_h.send(bytes(status, 'utf-8'))
                    connection_h.send(b'\nYou are registered successfully!!')
                else:
                    list_lock.release()
                    connection_h.send(bytes(status, 'utf-8'))
                    connection_h.send(
                        b'\nIrcRegistrationError1: This username is already in use.\nPlease enter  a different username')
            elif intent != 'register':
                connection_h.send(b'\nPlease enter a username to proceed')
        print(user_list)
        client_handler(connection_h, port_m)


####################################################################################################

def get_temp_socket(member, temp_port):
    sock = socket()
    try:
        sock.connect((gethostname(), temp_port))
    except ConnectionError:
        #	except OSError:
        exp_handle(temp_port)
    return sock


def send_msg(msg, member):
    message_socket = get_temp_socket(member, user_list[member])
    try:
        message_socket.send(bytes(msg, 'utf-8'))
    except ConnectionError:
        #	except OSError:
        exp_handle(user_list[member])
    if msg.split(' ')[0] == 'secure-msg':
        return message_socket

    message_socket.close()
    return


def quit_routine(connection_h, uid):
    connection_h.close()
    time.sleep(2)
    del_list = []
    for room_members in hallway.values():
        if uid in room_members:
            room_members.remove(uid)
    if uid in user_list:
        del user_list[uid]
    if uid in file_transfer_keys:
        del file_transfer_keys[uid]
    for user in user_list.keys():
        msg = '\nUser ' + uid + ' left IRC\n' + user + ': '
        send_msg(msg, user)
    for room, member_list in hallway.items():
        if len(member_list) == 0:
            del_list.append(room)
    for room in del_list:
        del hallway[room]
    return


def join_room_routine(connection_h, room, uid):
    if room not in hallway:
        hallway[room] = [uid]
        connection_h.send(b'\nYou joined a newly created room')
    else:
        for member in hallway[room]:
            msg = '\nUser ' + uid + ' joined room ' + room + '\n' + member + ': '
            send_msg(msg, member)
        hallway[room].append(uid)
        connection_h.send(b'\nYou joined an existing room')

    print(hallway)


def exit_routine(room, uid):
    hallway[room].remove(uid)
    if len(hallway[room]) == 0:
        del hallway[room]
    else:
        for member in hallway[room]:
            msg = '\nUser ' + uid + ' left room ' + room + '\n' + member + ': '
            send_msg(msg, member)
    return


def chat_room_routine(room, user, message):
    msg = '\n' + user + ' @ ' + room + ' says: ' + message
    room = hallway[room][:]
    room.remove(user)
    for member in room:
        send_msg(msg + '\n' + member + ': ', member)
    return


def list_routine(connection_h, List):
    List = str(list(List))
    connection_h.send(pack('L', len(List)))
    connection_h.send(bytes(List, 'utf-8'))
    return


def exp_handle(port_m):
    del_list = []
    if port_m in port_map:
        uid = port_map[port_m]
        del port_map[port_m]
    else:
        return
    if uid in file_transfer_keys:
        del file_transfer_keys[uid]
    for room_members in hallway.values():
        if uid in room_members:
            room_members.remove(uid)
    if uid in user_list:
        del user_list[uid]
    for user in user_list.keys():
        msg = '\nUser ' + uid + ' left IRC\n' + user + ': '
        send_msg(msg, user)
    for room, member_list in hallway.items():
        if len(member_list) == 0:
            del_list.append(room)
    for room in del_list:
        del hallway[room]
    return


def transfer_routine(sender, receiver, ext, size, File):
    try:
        file_socket = get_temp_socket(receiver, user_list[receiver] + 1)
        file_socket.send(pack('L', len(' '.join([sender, ext]))))
        file_socket.send(bytes(' '.join([sender, ext]), 'utf-8'))
        file_socket.send(pack('L', size))
        file_socket.send(File)
    except ConnectionError:
        #	except OSError:
        exp_handle(user_list[receiver])
        send_msg('Could not send file to ' + receiver + ' due to Connection Error\n' + sender + ': ', sender)


def secure_routine(sender, receiver, message, size):
    try:
        message_socket = send_msg('secure-msg ' + sender, receiver)
        message_socket.recv(2)
        message_socket.send(pack('L', size))
        message_socket.send(message)
        message_socket.close()
    except ConnectionError:
        #	except OSError:
        exp_handle(user_list[receiver])
        send_msg('Could not send secure message to ' + receiver + ' due to Connection Error\n' + sender + ': ', sender)


####################################################################################################

def client_handler(connection_h, port_m):
    uid = port_map[port_m]
    while True:
        try:
            command = connection_h.recv(128).decode('ascii')
            command = command.split(' ')
        except ConnectionError:
            #	except OSError:
            exp_handle(port_m)
            _thread.exit()
        else:
            intent = command[0]

        if intent == 'quit-irc':
            send_msg('\nYou are exiting out of IRC\nHope you had fun!', uid)
            quit_routine(connection_h, uid)
            break

        elif intent == 'join-room':
            join_room_routine(connection_h, command[1], uid)

        elif intent == 'exit-room':
            exit_routine(command[1], uid)

        elif intent == 'chat-room':
            try:
                message = connection_h.recv(448).decode('ascii')
            except ConnectionError:
                #	except OSError:
                exp_handle(port_m)
                _thread.exit()
            else:
                chat_room_routine(command[1], uid, message)

        elif intent == 'pvt-msg':
            try:
                message = connection_h.recv(448).decode('ascii')
            except ConnectionError:
                #	except OSError:
                exp_handle(port_m)
                _thread.exit()
            else:
                member = command[1]
                if member not in user_list:
                    msg = '\nIrcArgumentError3: Username ' + member + ' not found\n' + uid + ': '
                    send_msg(msg, uid)
                else:
                    msg = '\n' + uid + ' says: ' + message + '\n' + uid + ':'
                    send_msg(msg, command[1])

        elif intent == 'secure-msg':
            try:
                size = unpack('L', connection_h.recv(4))[0]
                #	size = unpack('L', connection_h.recv(8))[0]
                message = connection_h.recv(size)
            except ConnectionError:
                #	except OSError:
                exp_handle(port_m)
                _thread.exit()
            else:
                member = command[1]
                if member not in user_list:
                    msg = '\nIrcArgumentError3: Username ' + member + ' not found\n' + uid + ': '
                    send_msg(msg, uid)
                else:
                    secure_routine(uid, member, message, size)

        elif intent == 'list':
            if command[1] == 'rooms':
                if len(hallway) == 0:
                    msg = '\nNo rooms to display\n'
                    send_msg(msg, uid)
                list_routine(connection_h, hallway.keys())
            elif command[1] == 'users':
                list_routine(connection_h, user_list.keys())
            elif command[1] == 'members':
                if command[2] not in hallway:
                    msg = '\nIrcArgumentError3: Room ' + command[2] + ' not found\n' + command[-1] + ': '
                    send_msg(msg, uid)
                else:
                    list_routine(connection_h, hallway[command[2]])

        elif intent == 'set-file-transfer-key':
            file_transfer_keys[uid] = ' '.join(command[1:])
            connection_h.send(b'File transfer key set successfully\n')
            print(file_transfer_keys)

        elif intent == 'send-file':
            member = command[2]
            if member not in user_list:
                msg = '\nIrcArgumentError3: Username ' + member + ' not found\n' + uid + ': '
                send_msg(msg, uid)
                connection_h.send(b'Failed')
            elif member not in file_transfer_keys:
                msg = 'IrcFileTransferError1: ' + member + ' has not set a file transfer key\n'
                send_msg(msg, uid)
                connection_h.send(b'Failed')
            else:
                try:
                    connection_h.send(b'Not Failed')
                    connection_h.send(bytes('Enter ' + member + '\'s file transfer key: ', 'utf-8'))
                    key = connection_h.recv(16).decode('ascii')
                except ConnectionError:
                    #	except OSError:
                    exp_handle(port_m)
                if key == file_transfer_keys[member]:
                    connection_h.send(b'Success')
                    try:
                        size = unpack('L', connection_h.recv(4))[0]
                        #	size = unpack('L', connection_h.recv(8))[0]
                        File = connection_h.recv(size)
                    except ConnectionError:
                        #	except OSError:
                        exp_handle(user_list[sender])
                    ext = command[1].split('.')[-1]
                    start_new_thread(transfer_routine, (uid, member, ext, size, File))

                else:
                    connection_h.send(b'Failed')

        elif intent == 'broadcast':
            msg = uid + ' says: ' + connection_h.recv(448).decode('ascii')
            for user in user_list.keys():
                if user != uid:
                    send_msg(msg + '\n' + user + ': ', user)
    return


####################################################################################################

server_socket = socket()
server_socket.bind((gethostname(), 1234))
print('\nIRC server is listening . . .')
server_socket.listen()
while True:
    connection, address = server_socket.accept()
    port_m = port_h + 1
    port_f = port_h + 2

    handler_socket = socket()
    handler_socket.bind((gethostname(), port_h))
    connection.send(pack('L', port_h))
    handler_socket.listen()
    start_new_thread(initializer, (handler_socket, port_h,))

    port_h += 5
    