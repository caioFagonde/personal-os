import asyncio
from .main import startup, shutdown, seed_modules_from_manifests

async def main():
    await startup()
    await seed_modules_from_manifests()
    await shutdown()

if __name__ == "__main__":
    asyncio.run(main())
