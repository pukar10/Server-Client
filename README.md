# Server-Client
One thread is the Server (receiver) another thread is the Client (sender). provides in-order, reliable delivery of UDP datagrams 
in presence of packet loss and corruption. Sender delivers a file to server which verifies the integrity of the file.


## Approach
Server opens a UDP Socket and waits for packets. Client connects to socket and sends packets to server.


## Packet Types

###### DATA
1. type (unsigned integer): data or ack
2. seqNum (unsigned integer): sequence number
3. length (unsigned integer): length of data
4. checksum (unsigned integer): 4 bytes CRC

###### ACK 
- Same fields in its header, without any data.
