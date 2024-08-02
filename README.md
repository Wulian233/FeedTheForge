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
- **Git**: 3.8+
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

2. **Run**:
   - After installing the dependencies, run `__main__.py`

### Building Executable for Windows

1. **Package as Executable**:
   - To package the application as an executable for Windows, run the following script:
   - Windows
     ```bash
     cd PyBuild
     win_build.bat
     ```
   - Unix
     ```bash
     cd PyBuild
     unix_build.sh
     ```
2. **Locate the Executable**:
   - The resulting `.exe` file will be located in the `dist` folder.

3. **Additional Steps**:
   - Copy the `feedtheforge/lang` folder to the `dist` directory

## LICENSE
[GNU General Public License v3.0](.LICENSE)