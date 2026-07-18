import socket
import threading
import sys
import time

def handle_client(client_socket, allowed_slaves, port_number):
    try:
        while True:
            request = client_socket.recv(1024)
            if not request:
                break
            
            # Modbus TCP request is minimum 12 bytes
            if len(request) < 12:
                continue
                
            # Parse MBAP Header
            transaction_id = request[0:2]
            protocol_id = request[2:4]
            length = int.from_bytes(request[4:6], byteorder='big')
            unit_id = request[6]  # Slave ID (Unit Identifier)
            
            # Parse PDU
            function_code = request[7]
            
            # If unit_id is not allowed on this gateway, ignore to simulate connection timeout
            if unit_id not in allowed_slaves:
                print(f"[Port {port_number}] Ignoring request for Slave ID {unit_id} (allowed: {allowed_slaves})")
                continue
                
            if function_code == 3:  # Read Holding Registers
                start_address = int.from_bytes(request[8:10], byteorder='big')
                quantity = int.from_bytes(request[10:12], byteorder='big')
                
                # Build mock registers payload
                byte_count = quantity * 2
                data = bytearray()
                for i in range(quantity):
                    # Generate a mock stable value based on address and slave ID
                    val = (start_address + i + unit_id * 10) % 65535
                    data.extend(val.to_bytes(2, byteorder='big'))
                    
                # Build response frame (MBAP + response PDU)
                response_len = 1 + 1 + 1 + byte_count  # unit_id + fc + byte_count + data
                response = bytearray()
                response.extend(transaction_id)
                response.extend(protocol_id)
                response.extend(response_len.to_bytes(2, byteorder='big'))
                response.append(unit_id)
                response.append(function_code)
                response.append(byte_count)
                response.extend(data)
                
                client_socket.sendall(response)
            else:
                # Unsupported function code response (Modbus Exception 1)
                error_response = bytearray()
                error_response.extend(transaction_id)
                error_response.extend(protocol_id)
                error_response.extend((3).to_bytes(2, byteorder='big'))
                error_response.append(unit_id)
                error_response.append(function_code + 0x80)  # Exception flag
                error_response.append(1)  # Exception code (illegal function)
                client_socket.sendall(error_response)
    except Exception:
        pass
    finally:
        client_socket.close()

def start_server(port, allowed_slaves):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind(('127.0.0.1', port))
        server.listen(5)
        print(f"Modbus Simulator: Listening on 127.0.0.1:{port} (allowed Slave IDs: {allowed_slaves})")
        while True:
            client, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(client, allowed_slaves, port))
            t.daemon = True
            t.start()
    except Exception as e:
        print(f"Simulator Error on port {port}: {e}")
    finally:
        server.close()

if __name__ == "__main__":
    # Start thread for port 5020 (Slaves 1 & 2)
    t1 = threading.Thread(target=start_server, args=(5020, [1, 2]))
    t1.daemon = True
    t1.start()
    
    # Start thread for port 5021 (Slaves 3 & 4)
    t2 = threading.Thread(target=start_server, args=(5021, [3, 4]))
    t2.daemon = True
    t2.start()
    
    print("Modbus TCP Simulator running. Press Ctrl+C to terminate.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping simulator...")
        sys.exit(0)
