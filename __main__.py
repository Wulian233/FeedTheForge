if __name__ == "__main__":
    import asyncio
    import sys
    from main import *
    py_version = sys.version_info
    # main.py L14; feedtheforge/i18n.py 类型标注为Python 3.8新功能
    # lang.getdefaultlang已弃用，将在Python 3.15（2026年）删除 -> const.py L6
    if not (3, 8) < py_version < (3, 15):
        input(lang.t("feedtheforge.main.unsupported_version", 
                       cur=f"{py_version.major}.{py_version.minor}.{py_version.micro}"))
        exit(0)
    asyncio.run(main())
    