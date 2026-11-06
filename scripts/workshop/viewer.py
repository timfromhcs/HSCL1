"""Tk window that shows the newest VM frame. Usage: viewer.py FRAME.png STATUS.txt TITLE
Polls the files twice per second, scales the picture to the window, closes itself when the frame file stops changing for 5 minutes
or the window is closed. Standard library only (tkinter reads PNG natively)."""
import sys
import time
import tkinter as tk
from pathlib import Path


def main() -> int:
    frame, status, title = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else "VM"
    root = tk.Tk()
    root.title(f"HSCL1 VM live view - {title}")
    root.geometry("960x640+40+40")
    root.attributes("-topmost", True)
    label = tk.Label(root, bg="black")
    label.pack(fill="both", expand=True)
    bar = tk.Label(root, anchor="w", text="waiting for the first frame ...", font=("Segoe UI", 10))
    bar.pack(fill="x")
    state = {"mtime": 0.0, "img": None, "last_change": time.time()}

    def tick() -> None:
        try:
            m = frame.stat().st_mtime
            if m != state["mtime"]:
                img = tk.PhotoImage(file=str(frame))
                w = max(1, root.winfo_width())
                f = max(1, -(-img.width() // w))  # integer subsample so the frame fits the window width
                state["img"] = img.subsample(f, f) if f > 1 else img
                label.configure(image=state["img"])
                state["mtime"], state["last_change"] = m, time.time()
            txt = status.read_text(encoding="utf-8").strip() if status.exists() else ""
            bar.configure(text=f"{txt}   (frame {time.strftime('%H:%M:%S', time.localtime(state['mtime']))})" if state["mtime"] else bar.cget("text"))
        except (OSError, tk.TclError):
            pass
        if time.time() - state["last_change"] > 300 and state["mtime"]:
            root.destroy()
            return
        root.after(500, tick)

    tick()
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
