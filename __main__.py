if __name__ == "__main__":
    import asyncio
    import sys
    from main import *
    py_version = sys.version_info

    if not (3, 8) < py_version < (3, 15):
        print(lang.t("feedtheforge.main.unsupported_version", 
                       cur=f"{py_version.major}.{py_version.minor}.{py_version.micro}"))
        pause()
    asyncio.run(main())
    