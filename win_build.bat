pip install nuitka
nuitka --onefile --enable-console --enable-plugin=upx --show-progress --windows-icon-from-ico=.\icon.ico --output-file=FeedTheForge --include-data-dir=.\feedtheforge\lang=feedtheforge\lang __main__.py
