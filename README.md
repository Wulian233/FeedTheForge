<div align="center"> 
   <img height="100px" width="100px" alt="logo" src="PyBuild/icon.png"/> 
   <h1>Feed The Forge</h1>
</div>

## Introduce
This is a simple tool to download modpacks from FTB without the need of the FTB Launcher.

You can then import or drag this zip file into any curseforge compatible launcher. 

For example: HMCL, PCL2, Prism Launcher etc.

## Usage
WIP

## Develop and Build
### Requirements
- **Git**
- **Python Version**: 3.8+
- **Supported Operating Systems**: Windows 10 or later, macOS, Linux

### Running from Source

1. **Install Dependencies**:
   - Open a terminal and run the following command to install required packages:
     ```bash
     git clone https://github.com/Wulian233/FeedTheForge.git
     cd FeedTheForge
     pip install -r requirements.txt
     ```

2. **Run the Application**:
   - **Windows**: Use the command `python __main__.py`
   - **macOS and Linux**: Use the command `python3 __main__.py`

### Building Executable

1. **Package as Executable**:
     ```bash
     pip install pyinstaller
     pyinstaller main.spec
     ```
3. **Locate the Executable**:
   - For **Windows**, the executable will be a `.exe` file located in the `dist` folder.
   - For **macOS**, the application will be packaged as a `.app` bundle, also found in the `dist` folder.
   - For **Linux**, the executable will be a standalone file in the `dist` folder.


## LICENSE
[GNU General Public License v3.0](.LICENSE)