#Program modified by Steven Starovoitov/N01363509

import socket
import argparse
import struct
from collections import OrderedDict

def unpack_packet(packet):
    """Extract sequence number and data from packet"""
    if len(packet) < 4:
        return None, None
    seq_num = struct.unpack('!I', packet[:4])[0]
    data = packet[4:]
    return seq_num, data

def run_server(port, output_file):
    # 1. Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # 2. Bind the socket to the port
    server_address = ('', port)
    print(f"[*] Server listening on port {port}")
    print(f"[*] Server will save each received file as 'received_<ip>_<port>.jpg'")
    sock.bind(server_address)
    
    # increasing the buffer size for larger packets
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)

    try:
        while True:
            f = None
            sender_filename = None
            expected_seq = 0
            buffer = {}
            current_client = None
            
            print("[*] Waiting for file transfer...")
            
            while True:
                try:
                    sock.settimeout(30.0)
                    # buffer for 4096 bytes with some margin
                    packet, sender_addr = sock.recvfrom(4100)
                    sock.settimeout(None)
                    
                except socket.timeout:
                    print(f"[!] Timeout waiting for packets")
                    break
                
                # we'll check for empty packet
                if len(packet) == 0:
                    print(f"[*] Empty packet received, treating as EOF")
                    break
                
                # we'll extract sequence number and data
                seq_num, data = unpack_packet(packet)
                if seq_num is None:
                    continue
                
                # checking for special EOF marker
                if seq_num == 0xFFFFFFFF:
                    print(f"[*] EOF marker received")
                    # Flush buffer
                    while expected_seq in buffer:
                        buffered_data = buffer.pop(expected_seq)
                        if f:
                            f.write(buffered_data)
                        expected_seq += 1
                    break
                
                # tracking current client (via relay)
                if current_client is None:
                    current_client = sender_addr
                    ip, sender_port = sender_addr
                    sender_filename = f"received_{ip.replace('.', '_')}_{sender_port}.jpg"
                    f = open(sender_filename, 'wb')
                    print(f"[*] First packet from {sender_addr}. Writing to '{sender_filename}'")
                    print(f"[*] Packet size: {len(packet)} bytes, data: {len(data)} bytes")
                
                # sending ACK back to sender (relay)
                ack_packet = struct.pack('!I', seq_num)
                sock.sendto(ack_packet, sender_addr)
                
                # processing packet
                if seq_num == expected_seq:
                    # write out expected packet
                    if f:
                        f.write(data)
                    expected_seq += 1
                    
                    # process buffered packets
                    while expected_seq in buffer:
                        buffered_data = buffer.pop(expected_seq)
                        if f:
                            f.write(buffered_data)
                        expected_seq += 1
                        
                elif seq_num > expected_seq:
                    # buffer out-of-order packet
                    if seq_num not in buffer:
                        buffer[seq_num] = data
                        # added to avoid console spam
                        if len(buffer) < 5:
                            print(f"[*] Buffered packet {seq_num}, waiting for {expected_seq}")
                else:
                    # duplicate packet
                    if expected_seq < 10:
                        print(f"[*] Duplicate packet {seq_num}, expected {expected_seq}")
            
            # closing the file
            if f:
                f.close()
                if expected_seq > 0:
                    print(f"[✓] File saved: '{sender_filename}' ({expected_seq} packets)")
                else:
                    print(f"[!] No data received for file")
            
            print("==== End of reception ====")
            #reset for next transfer
            expected_seq = 0
            buffer.clear()
            current_client = None
            
    except KeyboardInterrupt:
        print("\n[!] Server stopped manually.")
    except Exception as e:
        print(f"[!] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        sock.close()
        print("[*] Server socket closed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reliable UDP File Receiver with RDT")
    parser.add_argument("--port", type=int, default=12001, help="Port to listen on")
    parser.add_argument("--output", type=str, default="received_file.jpg", help="File path to save data")
    args = parser.parse_args()

    try:
        run_server(args.port, args.output)
    except KeyboardInterrupt:
        print("\n[!] Server stopped manually.")
    except Exception as e:
        print(f"[!] Error: {e}")