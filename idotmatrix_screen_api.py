#!/usr/bin/env python3

import asyncio
import sys

from os import environ
from fastapi import FastAPI
from idotmatrix import ConnectionManager

IDMMAC = environ.get("IDMMAC")
if not IDMMAC:
    print("FATAL ERROR: IDMMAC environment variable is not set.", file=sys.stderr)
    sys.exit(1)


async def idm_screen(mac, state):
    try:
        conn = ConnectionManager()
        data = {"on": bytearray([5, 0, 7, 1, 1]), "off": bytearray([5, 0, 7, 1, 0])}
        await conn.connectByAddress(mac)
        await conn.send(data=data[state])
        await conn.disconnect()
    except Exception as e:
        print(f"{e}")
        await conn.disconnect()
    return True


app = FastAPI()


@app.get("/idm_on")
async def turn_on():
    return await idm_screen(IDMMAC, "on")


@app.get("/idm_off")
async def turn_off():
    return await idm_screen(IDMMAC, "off")
