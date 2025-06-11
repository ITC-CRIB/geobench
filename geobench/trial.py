import asyncio

async def a():
    await asyncio.sleep(5)
    print("a")
    

async def b():
    await asyncio.sleep(1)
    print("b")
    

tasks = [a(), b()]


async def main():
    await asyncio.gather(*tasks)

asyncio.run(main())
