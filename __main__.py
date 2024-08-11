if __name__ == "__main__":
    import asyncio
    import sys
    from feedtheforge.const import lang
    from feedtheforge.main import main
    from feedtheforge.utils import pause

    py_version = sys.version_info

    if not (3, 8) < py_version < (3, 15):
        from colorama import Fore, just_fix_windows_console

        just_fix_windows_console()
        
        print(Fore.RED + lang.t("feedtheforge.main.unsupported_version", 
                       cur=f"{py_version.major}.{py_version.minor}.{py_version.micro}"))
        pause()
    asyncio.run(main())
    