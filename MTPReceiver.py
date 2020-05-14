import unreliable_channel
import sys
import threading
import unreliable_channel
import zlib as z
import socket
import bitstring as bitstring

global expectedSeq
global Rptype
global Rlen
global Rcheck
global status

tempL = 0
c = 0
seqNum = 0
dataLength = 16
global checksum

# open log file and start logging
rlog = open("Receiver-log-file.txt", "w")


# extract the packet data after receiving
def extract_packet_info(packet):
    global expectedSeq
    global Rptype
    global Rlen
    global Rcheck
    global status
    global c
    global tempL

    MTPH = packet[:16]

    Rptype = MTPH[:2]
    MTPH = MTPH[2:]
    expectedSeq = MTPH[:2]
    MTPH = MTPH[2:]
    Rlen = MTPH[:4]
    MTPH = MTPH[4:]
    Rcheck = MTPH

    x = Rptype + expectedSeq + Rlen
    c = z.crc32(x)
    c = hex(c)
    c = c[2:]

    if len(packet) > 1472:
        status = -1
    else:
        status = 0


# Two types of packets, data and ack
# crc32 available through zlib library
def create_packet():
    global status
    global seqNum
    global dataLength
    global checksum

    DataL = hex(dataLength)
    x = DataL + '0001' + str(seqNum)  # Sum of all three other variables
    x = bitstring.BitArray(x)
    checksum = z.crc32(x.tobytes())
    checksum = hex(checksum)
    checksum = checksum[2:]

    if seqNum < 10:
        packetType = '%02x' % 0x1
        seqN = '%02x' % seqNum
        DataL = DataL[2:]
        DataL = '00' + DataL
        MTPheader = packetType + seqN + DataL + checksum
    elif seqNum > 99:
        DataL = DataL[2:]
        DataL = '00' + DataL
        MTPheader = '1' + str(seqNum) + DataL + checksum
    else:
        packetType = '%02x' % 0x1
        DataL = DataL[2:]
        DataL = '00' + DataL
        MTPheader = packetType + str(seqNum) + DataL + checksum

    # if status < 0:
    # 	MTPheader += 'C'

    return MTPheader


def main():
    global seqNum
    global expectedSeq
    global Rptype
    global Rlen
    global Rcheck
    global status
    global tlog
    global rlog

    # read the command line arguments
    # if len(sys.argv) == 3:
    # 	receiverPort = sys.argv[1]
    # 	outputFile = sys.argv[2]
    # 	receiverLog = sys.argv[3]
    # else:
    # 	print("Wrong number of inputs")
    # 	sys.exit(0)

    receiverIP = ''
    receiverPort = 1058
    inputFile = 'temp.txt'
    rlog = open(inputFile, "w")

    time = 0.5  # this represents 500ms

    # open server socket and bind
    Receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    Receiver_socket.bind((receiverIP, receiverPort))

    # receive packet, but using our unreliable channel
    # check for corruption and lost packets, send ack accordingly
    while True:
        try:
            Receiver_socket.settimeout(time)
            packet_from_server, server_addr = unreliable_channel.recv_packet(Receiver_socket)

            # if packet_from_server == 'done':
            #     print('All Done')
            #     break
            if packet_from_server[:2] == b'do':  # end when last packet is sent (with the done thingy)
                print("All Done")
                break
            extract_packet_info(packet_from_server)
            # log start
            p = packet_from_server
            if p[:2] != b'do':  # end packet sent
                rlog.write("Packet Received | type = Data | seqNum = " + str(int(p[2:4])) + " | length: " + str(len(p))
                           + " | checksum in packet: " + str(p[9:17].decode("utf-8")) + " | checksum Calculated:  " +
                           str(p[9:17].decode("utf-8")) + " | status: ")
            # log end
            if int(expectedSeq) > seqNum or status == -1:
                ACKPacket = create_packet()
                print('corrupted ack ' + ACKPacket)
                # log start
                rlog.write("CORRUPT\n")
                # log end
                x = bitstring.BitArray(ACKPacket.encode('utf-8'))
                unreliable_channel.send_packet(Receiver_socket, x.tobytes(), server_addr)
            else:
                ACKPacket = create_packet()
                seqNum += 1
                # print(ACKPacket)
                # log start
                rlog.write("NOT_CORRUPT\n")
                # log end
                x = bitstring.BitArray(ACKPacket.encode('utf-8'))
                unreliable_channel.send_packet(Receiver_socket, x.tobytes(), server_addr)
                # log start
                if p[:2] != b'do':
                    rlog.write("Packet Sent | type = ACK | seqNum = " + str(int(p[2:4])) + " | length: " + str(len(p)) +
                               " | checksum in packet: " + str(p[9:17].decode("utf-8")) + "\n")
                # log end
        except socket.timeout:
            print('Waiting for next packet')
            continue
    rlog.close()


if __name__ == '__main__':
    main()
