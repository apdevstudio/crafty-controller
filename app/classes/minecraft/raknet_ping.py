from contextlib import redirect_stderr
import os
import socket
import time

from app.classes.shared.null_writer import NullWriter

with redirect_stderr(NullWriter()):
    import psutil


class RaknetPing:
    magic = b"\x00\xff\xff\x00\xfe\xfe\xfe\xfe\xfd\xfd\xfd\xfd\x12\x34\x56\x78"
    fields = {  # (len, signed)
        "byte": (1, False),
        "long": (8, True),
        "ulong": (8, False),
        "magic": (16, False),
        "short": (2, True),
        "ushort": (2, False),  # unsigned short
        "string": (2, False),  # strlen is ushort
        "bool": (1, False),
        "address": (7, False),
        "uint24le": (3, False),
    }
    byte_order = "big"

    def __init__(self, server_addr, server_port, client_guid=0, timeout=5):
        self.addr = server_addr
        self.port = server_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(timeout)
        self.proc = psutil.Process(os.getpid())
        self.guid = client_guid
        self.guid_bytes = self.guid.to_bytes(8, RaknetPing.byte_order)

    @staticmethod
    def __byter(in_val, to_type):
        f = RaknetPing.fields[to_type]
        return in_val.to_bytes(f[0], RaknetPing.byte_order, signed=f[1])

    @staticmethod
    def __slice(in_bytes, pattern):
        ret = []
        bytes_index = 0
        pattern_index = 0
        while bytes_index < len(in_bytes):
            try:
                field = RaknetPing.fields[pattern[pattern_index]]
            except IndexError as index_error:
                raise IndexError(
                    "Ran out of pattern with additional bytes remaining"
                ) from index_error
            if pattern[pattern_index] == "string":
                string_header_length = field[0]
                string_length = int.from_bytes(
                    in_bytes[bytes_index : bytes_index + string_header_length],
                    RaknetPing.byte_order,
                    signed=field[1],
                )
                length = string_header_length + string_length
                ret.append(
                    in_bytes[
                        bytes_index
                        + string_header_length : bytes_index
                        + string_header_length
                        + string_length
                    ].decode("ascii")
                )
            elif pattern[pattern_index] == "magic":
                length = field[0]
                ret.append(in_bytes[bytes_index : bytes_index + length])
            else:
                length = field[0]
                ret.append(
                    int.from_bytes(
                        in_bytes[bytes_index : bytes_index + length],
                        RaknetPing.byte_order,
                        signed=field[1],
                    )
                )
            bytes_index += length
            pattern_index += 1
        return ret

    @staticmethod
    def __get_time():
        # return time.time_ns() // 1000000
        return time.perf_counter_ns() // 1000000

    def __sendping(self):
        pack_id = RaknetPing.__byter(0x01, "byte")
        now = RaknetPing.__byter(RaknetPing.__get_time(), "ulong")
        guid = self.guid_bytes
        d2s = pack_id + now + RaknetPing.magic + guid
        # print("S:", d2s)
        self.sock.sendto(d2s, (self.addr, self.port))

    def __recvpong(self):
        data = self.sock.recv(4096)
        if data[0] == 0x1C:
            ret = {}
            sliced = RaknetPing.__slice(
                data, ["byte", "ulong", "ulong", "magic", "string"]
            )
            if sliced[3] != RaknetPing.magic:
                raise ValueError(f"Incorrect magic received ({sliced[3]})")
            ret["server_guid"] = sliced[2]
            ret["server_string_raw"] = sliced[4]
            server_info = sliced[4].split(";")
            ret["server_edition"] = server_info[0]
            ret["server_motd"] = (server_info[1], server_info[7])
            ret["server_protocol_version"] = server_info[2]
            ret["server_version_name"] = server_info[3]
            ret["server_player_count"] = server_info[4]
            ret["server_player_max"] = server_info[5]
            ret["server_uuid"] = server_info[6]
            ret["server_game_mode"] = server_info[8]
            ret["server_game_mode_num"] = server_info[9]
            ret["server_port_ipv4"] = server_info[10]
            ret["server_port_ipv6"] = server_info[11]
            return ret
        raise ValueError(f"Incorrect packet type ({data[0]} detected")

    def ping(self, retries=3):
        rtr = retries
        while rtr > 0:
            try:
                self.__sendping()
                return self.__recvpong()
            except ValueError as e:
                print(
                    f"E: {e}, checking next packet. Retries remaining: {rtr}/{retries}"
                )
            rtr -= 1
