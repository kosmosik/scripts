#!/usr/bin/env python3

import asyncio
import argparse

from idotmatrix import ConnectionManager

parser = argparse.ArgumentParser()
parser.add_argument("mac")
parser.add_argument("status", choices=["on", "off"])
args = parser.parse_args()


async def main(mac, status):
    conn = ConnectionManager()
    data = {"on": bytearray([5, 0, 7, 1, 1]), "off": bytearray([5, 0, 7, 1, 0])}
    await conn.connectByAddress(mac)
    await conn.send(data=data[status])
    await conn.disconnect()


asyncio.run(main(args.mac, args.status))
