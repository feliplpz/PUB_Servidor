import bluetooth
import json

def recv_all(sock, length):
    data = b''
    while len(data) < length:
        more = sock.recv(length - len(data))
        if not more:
            return None
        data += more
    return data

def main():
    server_socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    server_socket.bind(('', bluetooth.PORT_ANY))

    server_socket.listen(1)
    name = server_socket.getsockname()[1]
    uuid = "043f618d-73ab-4878-9264-e34803bd0cd7"

    print('Server on name', name)
    print('...')
    
    while True:
        print("Aguardando conexão...")

        socket, info = server_socket.accept()
        print('Conexão aceita de', info)

        while True:
            try:
                length_bytes = recv_all(socket, 4)
                if not length_bytes:
                    print('Erro: Não conseguiu receber 4 bytes para o comprimento da mensagem.')
                    break

                length = int.from_bytes(length_bytes, byteorder='big')

                if length <= 0:
                    print('Erro: Comprimento inválido recebido.')
                    break

                message_bytes = socket.recv(length)
                if len(message_bytes) < length:
                    print('Erro: Não conseguiu receber a mensagem completa.')
                    break

                message_json = str(message_bytes, 'utf-8')
                message = json.loads(message_json)

                print('Mensagem recebida:', message)

            except bluetooth.btcommon.BluetoothError as bt_err:
                print(f'Erro Bluetooth: {bt_err}')
                if bt_err.errno == 11:
                    continue  # Tenta novamente se o recurso estiver temporariamente indisponível
                else:
                    break  # Sai do loop interno se for outro erro

        print('Conexão encerrada.')
        socket.close()

if __name__ == '__main__':
    main()
