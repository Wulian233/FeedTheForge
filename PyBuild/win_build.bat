@echo off
cd..
pip install -r requirements.txt 
pip install pyinstaller
pyinstaller main.spec