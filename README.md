# Sims 4 Workspace

One project to manage all your The Sims 4 mods. This will assist with decompiling the game's python scripts and compiling
your mods for development and for release.

## Cloning the Repository and Initial Setup

To get started, clone the repository and initialize the submodule:

```sh
git clone https://github.com/ssinakhot/sims4-workspace.git
cd sims4-workspace
git submodule update --init --recursive
```

## Updating the Submodule

To update the submodule to the latest version, use the following commands:

```sh
cd sims4-workspace
git submodule update --remote
```
 
## Loading the Project from WSL

To load the project from WSL using VSCode, follow these steps:

1. Open your WSL terminal and navigate to your home directory or any directory where you want to clone the project:
    ```sh
    cd ~
    ```

2. Clone the repository from within WSL using the instructions above.

3. Run the setup script to configure the environment:
    ```sh
    ./wsl-setup.sh
    ```

4. Open VSCode and use the Remote - WSL extension to open the project folder:
    ```sh
    code .
    ```

5. Once the project is open in VSCode, you can open it in the devcontainer by selecting the `Reopen in Container` option from the Command Palette (Ctrl+Shift+P).

This will set up the development environment inside a container, allowing you to work on the project seamlessly.
## Scripts

### compile.py
This compiles and packages your `src` folder and creates a `build` folder containing your packaged mod ready for 
deployment. It then copies your packaged mod to the games Mods folder under it's own sub-folder 
`Mods/YourName_ProjectName/YourName_ProjectName.ts4script`.

### decompile.py
This decompiles the game's python scripts and places them into a global projects folder. Throughout the process it prints 
a pretty progress meter and at the end of each module it decompiled it shows the success and fail stats as well as how 
long it took. It does this again at the end of the whole decompilation. It also clears out the old decompiled files for 
you and overall makes everything very smooth and simple.

### debug_setup.py and debug_teardown.py

These create and remove a debugging environment so that you can debug your game with a real debugger. The only downside
is that it requires PyCharm Pro, which is a paid program that costs money. There's no other known way to do this. If
you have PyCharm Pro then this will access the debugging capability in it and create 2 mods.

* `pycharm-debug-capability.ts4script` which gives the Sims 4 capability to debug by connecting to PyCharm Pro
* `pycharm-debug-cmd.ts4script` which creates a cheat code `pycharm.debug` you can enter in-game which will active
debugging for the rest of the game.

Both the cheatcode and `debug_setup.py` give clear and well-written instructions informing you of what to do and how
to set it up or what to expect. I've also written a 
[tutorial](https://medium.com/analytics-vidhya/the-sims-4-modern-python-modding-debugging-3736b37dbd9f) on how to
use it.

As the instructions say, run `debug_teardown.py` when not debugging because it can otherwise slow down your game.
Sigma1202 is the person who discovered this, I just made it into a script.

### devmode.py

This enters into a special mode called "Dev Mode", it clears out compiled code and links your src folder to the 
Mod Folder. When Dev Mode is activated, you don't need to compile anymore. If you run `compile.py` though it will exit 
Dev Mode and do a normal compile.

When inside of Dev Mode you can enter the cheat `devmode.reload [path.to.module]`, it'll reload the file live while
the game is running so it doesn't need to be closed and re-opened. For example, to reload main.py enter 
`devmode.reload main`. You can also enter paths to folders which will reload the entire folder or just not specify a 
path which will reload the entire project.

This only works in devmode.

### fix_tuning_names.py

This expects you to have extracted the tuning files from `Sims 4 Studio` with the `Sub-Folders` option checked. What 
this does is go through each and every tuning file and rename it to a much cleaner and better name.

### sync_packages.py

Running this script searches the top-level assets folder for any `.package` files and then copies them to your
Mod Name Folder alongside your scripts. It's automatically run with `compile.py` and `devmode.py` and you can run it
anytime yourself.

### bundle_build.py

Zips up the build artifacts in a way that can be sent to Sims 4 Players or Mod Websites. It nests all the build 
artifacts in a subfolder named `CreatorName_ProjectName`. This way the player can directly unzip your mod into the Mods
folder and it will all be self-contained in it's own folder.

### cleanup.py

Removes all build artifacts

* The build folder
* The Mod Name folder in Mods
* Debug functionality

When completed, all traces of anything built by the project template for your mod will be removed leaving a fresh slate.
This is common when you just want to clean everything up, especially after your all done developing and want to
essentially "Un-Build" and "Un-Make" everything.

### src/helpers/injector.py

This uses the popular injector, brought to my attention by LeRoiDesVampires and TURBOSPOOK. It's widely used in the Sims
modding community across mods and tools. Reference it in your code to automate replacing functions in-game in a much
prettier way with less coding. Optional to use.

## How to get started with this

1. Download it to your computer wherever you like, this will be your project folder for one project.
2. Rename the folder to the name of your project.
3. Copy `settings.py.example` to another file called `settings.py`, this will become your personal settings.
3. Update the settings to match your needs.
4. If you don't already have the library decompiled, run `decompile.py`.
5. Using your favorite editor whether it be `Sublime`, `Notepad++`, `Visual Studio Code`, `PyCharm`, or wherever begin
adding files to the `src` folder. 
6. Run `compile.py` and test it out. 

## Credits

Project [Sims4ScriptingBPProj](https://github.com/junebug12851/Sims4ScriptingBPProj)\
Copyright (c) 2021 [junebug12851](https://github.com/junebug12851)\
Licensed [Apache2](https://www.apache.org/licenses/LICENSE-2.0)

Project [Sims4ScriptingTemplate](https://github.com/mycroftjr/Sims4ScriptingTemplate)\
Copyright (c) 2023 [mycroftjr](https://github.com/mycroftjr)\
Licensed [Apache2](https://www.apache.org/licenses/LICENSE-2.0)

