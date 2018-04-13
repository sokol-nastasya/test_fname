import socket

import bitstring as bitstring


ip = "192.168.10.33"
port = 554
adr = "rtsp://192.168.10.33:554/live.sdp"
client_ports = [56554, 56555]
fname = "stream1.h264"
rn = 5000

op = "OPTIONS " + adr + " RTSP/1.0\r\nCSeq: 1\r\nUser-Agent: python\r\nRequire: implicit-play\r\nProxy-Require: gzipped-messages\r\n\r\n"
des = "DESCRIBE " + adr + " RTSP/1.0\r\nCSeq: 2\r\n User-Agent: python \r\nAccept: application/adp \r\n\r\n"
set = "SETUP " + adr + "/trackID=1 RTSP/1.0\r\nCSeq: 3\r\nUser-Agent: python\r\nTransport: RTP/AVP;unicast;client_port=" + str(client_ports[0])+ "-" + str(client_ports[1])+ "\r\n\r\n"
ply = "PLAY " + adr + " RTSP/1.0\r\nCSeq: 4\r\nUser-Agent: python\r\nSession: session-id\r\n Range: npt=30-\r\n\r\n"
pas = "PAUSE " + adr + " RTSP/1.0\r\nCSeq: 5\r\nUser-Agent: python\r\nSession: session-id\r\n\r\n"
ter = "TEARDOWN " + adr + " RTSP/1.0\r\nCSeq: 6\r\nUser-Agent: python\r\nSession: session-id\r\n\r\n"

def sessionid(data):
    recs = data.decode().split("\r\n")
    for rec in recs:
        ss = rec.split()
        if (ss[0].strip() == "Session:"):
            return int(ss[1].split(";")[0].strip())

def setsesid(data, idn):
    return data.replace("session-id", str(idn))

def digestpacket(st):
    startbytes = b"\x00\x00\x00\x01"
    bt = bitstring.BitArray(bytes=st)
    lc = 12
    bc = 12*8

    version = bt[0:2].uint
    p = bt[3]
    x = bt[4]
    cc = bt[4:8].uint
    m = bt[9]
    pt = bt[9:16].uint
    sn = bt[16:32].uint
    timestamp = bt[32:64].uint
    ssrc = bt[64:96].uint

    print("version, p, x, cc, m, pt", version, p, x, cc, m, pt)
    print("sequence number, timestamp", sn, timestamp)
    cids = []
    for i in range (cc):
        cids.append(bt[bc:bc+32].uint)
        bc += 32; lc += 4;
        print("csrc identifiers:", cids)

    if(x):
        hid = bt[bc:bc+16].uint
        bc += 16; lc += 2;
        hlen = bt[bc:bc+16].uint
        bc+=16; lc+=2;
        print("ext. header id, header len", hid, hlen)
        hst = bt[bc:bc+32*hlen]
        bc +=32*hlen; lc += 4*hlen;

    fb = bt[bc]
    nri = bt[bc+1:bc+3].uint
    nlu0 = bt[bc:bc+3]
    typ = bt[bc+3:bc+8].uint
    print("F, NRI, Type :", fb, nri, typ)
    print("first three bits together :",bt[bc:bc+3] )

    if(typ == 7 or typ == 8):
        if(typ == 7):
            print(">>>>>> SPS packet")
        else:
            print(">>>>>> PPS packet")
        return startbytes + st[lc:]

    bc += 8; lc += 1;
    start = bt[bc]
    end = bt[bc+2]
    nlu1 = bt[bc+3:bc+8]

    if(start):
        print(">>>>first fragment found")
        nlu = nlu0 + nlu1
        head = startbytes + nlu.bytes
        lc += 1

    if (start == False and end == False):
        head = b""
        lc += 1
    elif (end == True):
        head = ""
        print("<<<<<last fragment found")
        lc += 1

    if (typ ==28):
        return head+st[lc:]
    else:
        try:
            raise Exception("unknown frame type for this")
        except Exception:
            print("Error")


sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((ip, port))

print("Send OPTIONS")
sock.send(op.encode("utf-8"))
data = sock.recv(1024)
print(data)
print("***********************")
print()

print("Send DESCRIBE")
sock.send(des.encode("utf-8"))
data = sock.recv(1024)
print(data)
print("***********************")
print()

print("Send SETUP")
sock.send(set.encode("utf-8"))
data = sock.recv(1024)
print(data)
print("***********************")
print()

idn = sessionid(data)

s1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s1.bind(("", client_ports[0]))

print("Send PLAY")
ply = setsesid(ply, idn)
sock.send(ply.encode("utf-8"))
data = sock.recv(1024)
print(data)
print("***********************")
print()

f = open(fname, "wb")
for i in range(rn):
    print()
    data = s1.recv(4096)
    st = digestpacket(data)
    print("dumping", len(st), "bytes")
    f.write(st)
f.close()

print("Send PAUSE")
pas = setsesid(pas, idn)
sock.send(pas.encode("utf-8"))
data = sock.recv(1024)
print(data)
print("***********************")
print()

print("Send TEARDOWN")
ter = setsesid(ter, idn)
sock.send(ter.encode("utf-8"))
data = sock.recv(1024)
print(data)
print("***********************")
print()

sock.close()
s1.close()
