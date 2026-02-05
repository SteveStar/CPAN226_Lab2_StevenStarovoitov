import socket
import argparse
import time
import os

def run_client(target_ip, target_port, input_file):
    # 1. Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = (target_ip, target_port)

    print(f"[*] Sending file '{input_file}' to {target_ip}:{target_port}")

    if not os.path.exists(input_file):
        print(f"[!] Error: File '{input_file}' not found.")
        return

    try:
        with open(input_file, 'rb') as f:
            while True:
                # Read a chunk of the file
                chunk = f.read(4096) # 4KB chunks
                
                if not chunk:
                    # End of file reached
                    break

                # Send the chunk
                sock.sendto(chunk, server_address)
                
                # Optional: Small sleep to prevent overwhelming the OS buffer locally
                # (In a perfect world, we wouldn't need this, but raw UDP is fast!)
                time.sleep(0.001)

        # Send empty packet to signal "End of File"
        sock.sendto(b'', server_address)
        print("[*] File transmission complete.")

    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Naive UDP File Sender")
    parser.add_argument("--target_ip", type=str, default="127.0.0.1", help="Destination IP (Relay or Server)")
    parser.add_argument("--target_port", type=int, default=12000, help="Destination Port")
    parser.add_argument("--file", type=str, required=True, help="Path to file to send")
    args = parser.parse_args()

    run_client(args.target_ip, args.target_port, args.file)