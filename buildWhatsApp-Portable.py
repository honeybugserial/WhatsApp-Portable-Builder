#!/usr/bin/env python3
# make_whatsapp_portable.py — build a portable Electron wrapper for WhatsApp Web

import ctypes, json, os, shutil, subprocess, sys, tempfile, urllib.request, zipfile
from pathlib import Path

APP_DIR = Path("WhatsApp-Electron")
APP_NAME = "WhatsAppPortabler"
UA_STRING = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
             "AppleWebKit/537.36 (KHTML, like Gecko) "
             "Chrome/128.0.0.0 Safari/537.36")

# ---------------- utilitiesing ----------------
def is_admin():
    try: return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception: return False

def which_any(names):
    for n in names:
        p = shutil.which(n)
        if p: return p
    return None

def run(cmd_list, cwd=None, check=True):
    print(f"    $ {' '.join(cmd_list)}")
    return subprocess.run(cmd_list, cwd=cwd, check=check)

def check_output(cmd_list, cwd=None):
    return subprocess.check_output(cmd_list, cwd=cwd, text=True).strip()

def fetch(url, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)

def prompt_yes_no(question, default_yes=True):
    d = "Y/n" if default_yes else "y/N"
    while True:
        ans = input(f"{question} [{d}]: ").strip().lower()
        if not ans: return default_yes
        if ans in ("y","yes"): return True
        if ans in ("n","no"):  return False
        print("Please answer y/n.")

def section(title):
    print("\n" + "="*60)
    print(f"[ {title} ]")
    print("="*60)

def info(msg): print(f"  [i] {msg}")
def ok(msg):   print(f"  [OK] {msg}")
def warn(msg): print(f"  [!] {msg}")
def fail(msg): print(f"  [X] {msg}")

# ---------------- Node/npm buttstrappers ----------------
def parse_ver_tuple(vstr): return tuple(int(x) for x in vstr.split("."))

def ensure_node():
    node = which_any(["node.exe","node"])
    npm  = which_any(["npm.cmd","npm"])
    if node and npm:
        try:
            nv = check_output([node,"--version"])
            pv = check_output([npm,"--version"])
            ok(f"Node.js {nv} / npm {pv}")
            return
        except: pass

    warn("Node.js/npm not found and it is needed.")
    if not prompt_yes_no("Download and install latest LTS Node.js?"):
        sys.exit("Node.js is required. Abortion.")

    idx_url="https://nodejs.org/dist/index.json"
    info(f"Fetching {idx_url}")
    with urllib.request.urlopen(idx_url) as r:
        data=json.loads(r.read().decode("utf-8"))
    lts=[d for d in data if d.get("lts")]
    lts.sort(key=lambda d: parse_ver_tuple(d["version"].lstrip("v")))
    ver=lts[-1]["version"].lstrip("v")
    base=f"https://nodejs.org/dist/v{ver}"
    tmpd=Path(tempfile.mkdtemp(prefix="node_bootstrap_"))

    if is_admin():
        msi=tmpd/f"node-v{ver}-x64.msi"
        url=f"{base}/node-v{ver}-x64.msi"
        info(f"Downloading MSI {url}")
        fetch(url,msi)
        info("Installing Node.js (silent MSI)")
        run(["msiexec.exe","/i",str(msi),"/qn"])
        node_dir=Path(os.environ.get("ProgramFiles",r"C:\Program Files"))/"nodejs"
        os.environ["PATH"]=str(node_dir)+os.pathsep+os.environ["PATH"]
    else:
        zipf=tmpd/f"node-v{ver}-win-x64.zip"
        url=f"{base}/node-v{ver}-win-x64.zip"
        info(f"Downloading portable ZIP {url}")
        fetch(url,zipf)
        dest=Path.cwd()/"node-portable"
        if dest.exists(): shutil.rmtree(dest)
        info(f"Extracting to {dest}")
        with zipfile.ZipFile(zipf) as z: z.extractall(Path.cwd())
        (Path.cwd()/f"node-v{ver}-win-x64").rename(dest)
        os.environ["PATH"]=str(dest)+os.pathsep+os.environ["PATH"]

    node=which_any(["node.exe","node"]); npm=which_any(["npm.cmd","npm"])
    if not node or not npm: sys.exit("Node/npm not available after bootstrap.")
    nv=check_output([node,"--version"]); pv=check_output([npm,"--version"])
    ok(f"Node.js {nv} / npm {pv}")

# ---------------- skeletons ----------------
def write_utf8(path:Path,content:str):
    path.write_text(content,encoding="utf-8",newline="\n")

def scaffold(allow_media:bool, icon_src:Path|None):
    APP_DIR.mkdir(parents=True,exist_ok=True)
    pkg_json="""{
  "name": "whatsapp-electron",
  "version": "4.20.0",
  "private": true,
  "main": "main.js",
  "scripts": { "start": "electron ." },
  "devDependencies": { "electron": "^31.0.0" }
}
"""
    main_js=f"""const {{ app, BrowserWindow, shell, session }} = require("electron");
const path = require("path");
if (!app.requestSingleInstanceLock()) app.quit();
app.setPath("userData", path.join(process.cwd(), "Data"));
function createWindow() {{
  const win = new BrowserWindow({{
    width: 1100, height: 750, backgroundColor: "#121212",
    autoHideMenuBar: true, title: "WhatsApp",
    webPreferences: {{
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true, nodeIntegration: false,
      sandbox: true, spellcheck: true
    }}
  }});
  const ua = "{UA_STRING}";
  win.webContents.setUserAgent(ua);
  win.loadURL("https://web.whatsapp.com");
  win.webContents.setWindowOpenHandler(({{
    url
  }}) => {{ shell.openExternal(url); return {{ action: "deny" }}; }});
  const allowMedia = {str(allow_media).lower()};
  session.defaultSession.setPermissionRequestHandler((wc, permission, cb) => {{
    if (permission === "media") return cb(allowMedia);
    cb(false);
  }});
}}
app.whenReady().then(createWindow);
app.on("second-instance", () => {{
  const w = BrowserWindow.getAllWindows()[0];
  if (w) w.focus();
}});
app.on("window-all-closed", () => app.quit());
"""
    preload_js="// Minimal preload; no Node exposure.\n"
    write_utf8(APP_DIR/"package.json",pkg_json)
    write_utf8(APP_DIR/"main.js",main_js)
    write_utf8(APP_DIR/"preload.js",preload_js)
    if icon_src and icon_src.exists() and icon_src.stat().st_size>0:
        shutil.copy2(icon_src,APP_DIR/"icon.ico"); ok("Icon copied")
    else: info("No icon provided (skipping --icon).")
    node=which_any(["node.exe","node"])
    run([node,"-e","require('./package.json'); console.log('package.json ok')"],cwd=APP_DIR)

# ---------------- Builderings ----------------
def build(open_explorer=True):
    npm=which_any(["npm.cmd","npm"]); npx=which_any(["npx.cmd","npx"])
    if not npm or not npx: sys.exit("npm/npx not found.")
    section("Installing Electron")
    run([npm,"install"],cwd=APP_DIR)
    section("Packaging app")
    icon_arg=[]
    if (APP_DIR/"icon.ico").exists() and (APP_DIR/"icon.ico").stat().st_size>0:
        icon_arg=["--icon=icon.ico"]
    dist=APP_DIR/"dist"
    if dist.exists(): shutil.rmtree(dist)
    cmd=[npx,"@electron/packager",".",APP_NAME,"--platform=win32","--arch=x64","--out","dist","--overwrite","--prune=true","--asar"]+icon_arg
    run(cmd,cwd=APP_DIR)
    out=APP_DIR/"dist"/f"{APP_NAME}-win32-x64"
    if not out.exists(): sys.exit("Packaging failed.")
    exe=out/f"{APP_NAME}.exe"
    ok(f"Built: {out}")
    if exe.exists(): ok(f"Run: {exe}")
    # Open dist folder in Explorer
    if open_explorer:
        try:
            section("Opening dist folder in Explorer")
            os.startfile(str(out))  # Windows-only
        except Exception as e:
            warn(f"Could not open Explorer automatically: {e}")

# ---------------- mains ----------------
def main():
    print("============================================================")
    print(" WhatsApp Portable Builderings")
    print("============================================================")
    allow_media=prompt_yes_no("Allow mic/camera inside the app?",default_yes=True)
    section("Checking prerequisites")
    ensure_node()
    section("Scaffoldingings project")
    icon_arg=Path(sys.argv[1]) if len(sys.argv)>1 else None
    scaffold(allow_media,icon_arg)
    build(open_explorer=True)
    section("Done. Completed")

if __name__=="__main__":
    main()
