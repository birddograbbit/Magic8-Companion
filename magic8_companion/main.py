import asyncio
from .utils.scheduler import start


def main():
    start()
    asyncio.get_event_loop().run_forever()


if __name__ == '__main__':
    main()
