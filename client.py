#Program modified by Steven Starovoitov/N01363509

import socket
import argparse
import time
import os
import struct

def run_client(target_ip, target_port, input_file):
    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2.0)
    
    # Increase buffer sizes
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)
    
    print(f"[*] Sending file '{input_file}' to {target_ip}:{target_port}")
    print(f"[*] Using Stop-and-Wait RDT through relay")
    print(f"[*] Note: Using 4092 byte chunks to fit relay buffer")

    if not os.path.exists(input_file):
        print(f"[!] Error: File '{input_file}' not found.")
        return

    try:
        with open(input_file, 'rb') as f:
            seq_num = 0
            packets_sent = 0
            retransmissions = 0
            
            while True:
                # read chunk, has to be 4092 bytes or less to fit in buffer
                chunk = f.read(4092)
                
                if not chunk:
                    # send the eof marker
                    print(f"[*] File read complete, sending EOF marker")
                    eof_header = struct.pack('!I', 0xFFFFFFFF)
                    
                    # Send eof multiple times (in case of loss)
                    for i in range(3):
                        sock.sendto(eof_header, (target_ip, target_port))
                        if i < 2:
                            time.sleep(0.1)
                    
                    print(f"[*] EOF sent")
                    break
                
                # create packet
                header = struct.pack('!I', seq_num)
                packet = header + chunk
                packet_size = len(packet)
                
                # verify packet fits in relay buffer
                if packet_size > 4096:
                    print(f"[!] ERROR: Packet {seq_num} too large: {packet_size} > 4096")
                    return
                
                # send with retries
                max_retries = 15
                ack_received = False
                
                for attempt in range(max_retries):
                    try:
                        # send packet
                        sock.sendto(packet, (target_ip, target_port))
                        packets_sent += 1
                        
                        if attempt == 0:
                            print(f"[.] Sending packet {seq_num} ({len(chunk)} bytes)")
                        
                        # wait for ack
                        ack_data, _ = sock.recvfrom(8)
                        
                        if len(ack_data) >= 4:
                            ack_seq = struct.unpack('!I', ack_data[:4])[0]
                            
                            if ack_seq == seq_num:
                                ack_received = True
                                if attempt > 0:
                                    print(f"[✓] Packet {seq_num} ACK'd after {attempt + 1} attempts")
                                    retransmissions += attempt
                                break
                            else:
                                print(f"[!] Wrong ACK: got {ack_seq}, expected {seq_num}")
                                # still accept it (packet arrived)
                                ack_received = True
                                break
                                
                    except socket.timeout:
                        if attempt < max_retries - 1:
                            print(f"[!] Timeout for packet {seq_num}, retry {attempt + 1}")
                        continue
                
                if not ack_received:
                    print(f"[!] Failed to send packet {seq_num} after {max_retries} attempts")
                    print(f"[!] Check if relay and server are running")
                    return
                
                # progress update every 50 packets
                if seq_num % 50 == 0 and seq_num > 0:
                    print(f"[*] Progress: {seq_num + 1} packets sent")
                
                seq_num += 1
        
        print(f"\n[✓] Transfer complete!")
        print(f"    Packets sent: {packets_sent}")
        print(f"    Unique packets: {seq_num}")
        print(f"    Retransmissions: {retransmissions}")
        if retransmissions > 0:
            print(f"    Loss rate: {(retransmissions/packets_sent)*100:.1f}%")

    except Exception as e:
        print(f"[!] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        sock.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reliable UDP File Sender with RDT")
    parser.add_argument("--target_ip", type=str, default="127.0.0.1", help="Relay IP address")
    parser.add_argument("--target_port", type=int, default=12000, help="Relay port")
    parser.add_argument("--file", type=str, required=True, help="Path to file to send")
    args = parser.parse_args()

    run_client(args.target_ip, args.target_port, args.file)