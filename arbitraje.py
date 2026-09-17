import sys
import ctypes
import logging
import customtkinter as ctk

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("arbitraje.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

try:
    myappid = 'mycompany.myproduct.subproduct.version' 
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except:
    pass

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

def main():
    from src.gui import ArbitrageBotGUI
    app = ArbitrageBotGUI()
    app.mainloop()

if __name__ == "__main__":
    main()
