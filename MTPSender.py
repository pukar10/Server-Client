import os
import sys
import threading
import unreliable_channel
import zlib as z
import socket
import bitstring as bitstring

seqNum = -1
dataLength = 1456
global checksum
global expectedSeq
global Rptype
global Rlen
global Rcheck
global status
global wStart
global counter
global windowSize
logT = 0  # used for logging
ack = []  # used for logging
pnumber = -1

# we will need a lock to protect against concurrent threads
lock = threading.Lock()

# open log file and start logging
slog = open("Sender-log-file.txt", "w")


# extract the packet data after receiving
def extract_packet_info(packet):
    global expectedSeq
    global Rptype
    global Rlen
    global Rcheck
    global status
    global logT

    MTPH = packet[:16]
    logT = MTPH

    if pnumber > 99:
        Rptype = MTPH[:1]
        MTPH = MTPH[1:]
        expectedSeq = MTPH[:3]
        MTPH = MTPH[3:]
        Rlen = MTPH[:4]
        MTPH = MTPH[4:]
        Rcheck = MTPH

    Rptype = MTPH[:2]
    MTPH = MTPH[2:]
    expectedSeq = MTPH[:2]
    MTPH = MTPH[2:]
    Rlen = MTPH[:4]
    MTPH = MTPH[4:]
    Rcheck = MTPH

    if len(packet) > 16:
        status = -1
    else:
        status = 0


def create_packet(data):
    global seqNum
    global dataLength
    global checksum

    seqNum += 1
    DataL = hex(dataLength)
    DATA = bitstring.BitArray(data.encode('utf-8'))
    x = DataL + '0000' + str(seqNum) + DATA  # Sum of all three other variables
    checksum = z.crc32(x.tobytes())
    checksum = hex(checksum)
    checksum = checksum[2:]

    if seqNum < 10:
        packetType = '%02x' % 0x0
        seqN = '%02x' % seqNum
        DataL = DataL[2:]
        DataL = '0' + DataL
        MTPheader = packetType + seqN + DataL + checksum
        MTPheader = MTPheader + data
    elif seqNum > 99:
        DataL = DataL[2:]
        DataL = '0' + DataL
        MTPheader = '0' + str(seqNum) + DataL + checksum
        MTPheader = MTPheader + data
    else:
        packetType = '%02x' % 0x0
        DataL = DataL[2:]
        DataL = '0' + DataL
        MTPheader = packetType + str(seqNum) + DataL + checksum
        MTPheader = MTPheader + data

    return MTPheader


# def extract_packet_info():
# # extract the packet data after receiving

# receive packet, but using our unreliable channel
def receive_thread(client_socket):
    global seqNum
    global dataLength
    global checksum
    global expectedSeq
    global Rptype
    global Rlen
    global Rcheck
    global status
    global wStart
    global counter
    global windowSize
    global pnumber
    global tripleD
    global ack

    rcounter = 0

    print('Start Receiving')

    lock.acquire()

    slog.write("\n")
    while rcounter < windowSize:
        try:

            packet_from_server, server_addr = unreliable_channel.recv_packet(client_socket)
            # print(packet_from_server)
            extract_packet_info(packet_from_server)
            # start log
            ack.insert(int(logT[2:4]), 1)
            slog.write("Packet Received: type: ACK | seqNum: " + str(int(logT[2:4])) + "\n")
            # end log
            rcounter += 1

        except socket.timeout:
            print('time out')
            # log start
            slog.write("Timeout for packet seqNum: " + str(int(logT[2:4])))
            break

    if int(expectedSeq) != pnumber:
        wStart = int(expectedSeq)

    lock.release()

    counter += wStart


def main():
    global seqNum
    global dataLength
    global checksum
    global expectedSeq
    global Rptype
    global Rlen
    global Rcheck
    global status
    global wStart
    global counter
    global windowSize
    global pnumber
    global ack

    # read the command line arguments
    # if len(sys.argv) == 5:
    # 	receiverIP = sys.argv[1]
    # 	receiverPort = sys.argv[2]
    # 	windowSize = sys.argv[3]
    # 	inputFile = sys.argv[4]
    # 	senderLog = sys.argv[5]
    # else:
    # 	print("Wrong number of inputs")
    # 	sys.exit(0)

    # set up logging array ignore
    for i in range(700):
        ack.insert(i, 0)

    receiverIP = '127.0.0.1'
    receiverPort = 1058
    windowSize = 10
    inputFile = '1MB.txt'
    # # list files in directory
    cwd = os.getcwd()  # Get the current working directory (cwd)
    files = os.listdir(cwd)  # Get all the files in that directory
    print("Files in %r: %s" % (cwd, files))


    RIP = ''

    time = 0.5  # this represents 500ms
    wStart = 0
    counter = 0

    # open client socket and bind
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.connect((receiverIP, receiverPort))

    # start receive thread
    recv_thread = threading.Thread(target=receive_thread, args=(client_socket,))
    recv_thread.start()

    # take the input file and split it into packets (use create_packet)
    AllMTP = []
    f = open(inputFile, 'r')
    x = f.read()
    print(len(x))

    for i in range(len(x) // dataLength):
        data = []
        data = x[:dataLength]
        packets = create_packet(data)
        AllMTP.append(packets)
        x = x[dataLength:]

    # Adds the left over of the data
    data = []
    data = x[:dataLength]
    MTPpacket = create_packet(data)
    AllMTP.append(MTPpacket)
    x = x[dataLength:]

    # there are packets to send, send packets to server using our unreliable_channel.send_packet()
    while counter <= len(AllMTP):
        try:

            for i in range(wStart, windowSize, 1):
                x = bitstring.BitArray(AllMTP[i].encode('utf-8'))
                unreliable_channel.send_packet(client_socket, x.tobytes(), (receiverIP, receiverPort))
                # log start
                s = AllMTP[i]
                slog.write("Packet Sent | Type: DATA | seqNum: " + str(int(s[2:4])) + " | length: " + str(len(s)) +
                           " | checksum: " + str(s[9:17]) + "\n")
                # log end
                client_socket.settimeout(time)
                if i == len(AllMTP) - 1:
                    break
            pnumber = i

            lock.acquire()
            # start log
            slog.write("Updating Window: " + "\n")
            slog.write("Window state: [")
            for i in range(wStart, wStart+60, 1):
                slog.write(str(i) + "(" + str(ack[i]) + "), ")
            # end log
            lock.release()

            print(str(wStart))
            print(str(windowSize))
            print(str(counter))
            break
        except socket.timeout:
            print('timmmm')
            break

    # To indicate we are done sending all of the packets
    y = "done"
    y = bitstring.BitArray(y.encode('utf-8'))
    unreliable_channel.send_packet(client_socket, y.tobytes(), (receiverIP, receiverPort))


if __name__ == '__main__':
    main()
