import asyncio

class Receiver:
    def __init__(self, host, port, username, password):
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    async def send_cmd_rx(self, cmd_val, reader, writer):
        writer.write(cmd_val.encode('utf-8') + b"\r\n")
        await writer.drain()
        response = await reader.readuntil(b"NGS-C60 Telnet W>")
        return response.decode('utf-8')

    async def configure_receiver(self, rx_mode):
        reader, writer = await asyncio.open_connection(self.host, self.port)
        await reader.readuntil(b"Enter User ID : ")
        writer.write(self.username.encode('utf-8') + b"\r\n")
        await writer.drain()
        await reader.readuntil(b"Enter Password : ")
        await self.send_cmd_rx(self.password, reader, writer)
        response = await self.send_cmd_rx(rx_mode, reader, writer)
        print(response)
        writer.write(b"exit\r\n")
        await writer.drain()
        writer.close()
        await writer.wait_closed()
        print(f"{rx_mode} activated")

