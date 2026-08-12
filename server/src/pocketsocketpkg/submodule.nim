# This is just an example to get you started. Users of your hybrid library will
# import this file by writing ``import nimsockpkg/submodule``. Feel free to rename or
# remove this file altogether. You may create additional modules alongside
# this file as required.

import dynlib
import std/files
import std/paths
import os
import mummy
import config

# Make a function prototype
type
  updateProc = proc () {.nimcall.}

var
  dll: LibHandle      # Library that's loaded
  update: updateProc  # Function to call, and reload
  loaded_template_str: string # = "<html><body style='background:#111;color:#ccc'>Hello, World!</body></html>"



proc print_headers(headers: HttpHeaders) =
  # Access request headers in an iterator
  for (key, value) in headers:
    echo "  ", key, " = ", value


proc getWelcomeMessage*(): string =
    let filepath_str = "banner.txt"
    let base_dir = os.getCurrentDir()
    # let base_dir = getAppDir()
    let filepath = Path(base_dir) / Path(filepath_str)

    if loaded_template_str.len > 0:
      return loaded_template_str
    else:
      echo "Template String is nil: ", loaded_template_str ,". Discovering: ", cast[string](filepath)
      if fileExists(filepath):
          result = readFile(cast[string](filepath))
          # result = readAll(filepath_str)
      else:
          result = "Hello, World!"


proc getLocalFileContents*(filepath_str: string): string =
    # let filepath_str = "banner.txt"
    # let base_dir = os.getCurrentDir()
    if config.template_dir.len != 0:
      let base_dir: string = config.template_dir 
      let filepath = Path(base_dir) / Path(filepath_str)
      echo "Fetching local file: ", cast[string](filepath)
      if fileExists(filepath):
          return readFile(cast[string](filepath))
          # result = readAll(filepath_str)
      else:
          echo "File not found: ", cast[string](filepath)  
    else:
      echo "Template directory not set. Using default template." 
    
    let default_template_value: string = """<body onload="ws=new WebSocket('ws://'+location.host).onmessage=e=>document.body.innerHTML=e.data" style="background:#111;color:#ccc">builtin</body>"""
    return default_template_value


proc getCachedLocalFileContents*(filepath_str:string): string =
  #https://forum.nim-lang.org/t/9379
  {.cast(gcsafe).}:
    if cstring(loaded_template_str) != nil:
      return loaded_template_str
    else:
      echo "Template String is nil: ", loaded_template_str ,". Discovering: ", filepath_str
      return getLocalFileContents(filepath_str)


proc setLoadedTemplate*(filepath_str:string): void =
  loaded_template_str = getLocalFileContents(filepath_str)
  echo "Template Set: ", filepath_str, " Len: ", $loaded_template_str.len


proc load_lib*() =
    let base_dir = os.getCurrentDir()
    # let base_dir = getAppDir()
    let filepath = Path(base_dir) / Path("lib/imp.dll")
    let func_name: string = "greet"
    echo "Load ", cast[string](filepath)
    dll = loadLib(cast[string](filepath))   # Change this for your OS
    if dll != nil:
      # Get the address where the `update()` proc is stored
      let updateAddr = dll.symAddr(cstring(func_name))
      if updateAddr != nil:
        update = cast[updateProc](updateAddr)
    # Run it
    if update != nil:
      update()
    else:
      echo "Wasn't able to load ", func_name ,"() from DLL."