import cv2
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import numpy as np
import hashlib
import base64
import matplotlib.pyplot as plt
from skimage.metrics import structural_similarity as ssim
import pyperclip
import wave

# ================= ENCRYPTION =================

def generate_key(password, length):
    key = hashlib.sha256(password.encode()).digest()
    return (key * (length // len(key) + 1))[:length]

def encrypt_message(message, password):
    msg_bytes = message.encode()
    key = generate_key(password, len(msg_bytes))
    encrypted = bytes([m ^ k for m, k in zip(msg_bytes, key)])
    return base64.b64encode(encrypted).decode()

def decrypt_message(enc_message, password):
    try:
        enc_bytes = base64.b64decode(enc_message)
        key = generate_key(password, len(enc_bytes))
        decrypted = bytes([e ^ k for e, k in zip(enc_bytes, key)])
        return decrypted.decode(errors="ignore")
    except:
        return None

# ================= HELPERS =================

def text_to_bin(text):
    return ''.join(format(ord(i), '08b') for i in text)

def bin_to_text(binary):
    chars = [binary[i:i+8] for i in range(0, len(binary), 8)]
    message = ""
    for c in chars:
        message += chr(int(c, 2))
        if "###END###" in message:
            return message.replace("###END###", "")
    return ""

# ================= METRICS =================

def calculate_metrics(original, stego):
    mse = ((original - stego) ** 2).mean()
    psnr = 100 if mse == 0 else 20 * np.log10(255.0 / np.sqrt(mse))
    gray1 = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(stego, cv2.COLOR_BGR2GRAY)
    ssim_val = ssim(gray1, gray2)
    return psnr, mse, ssim_val

# ================= GLOBAL =================
selected_image = None
original_image = None

# ================= LOAD =================

def load_image():
    global selected_image, original_image
    path = filedialog.askopenfilename()
    if not path:
        return

    selected_image = path
    original_image = cv2.imread(path)

    img = Image.open(path).resize((300,300))
    img = ImageTk.PhotoImage(img)
    panel.config(image=img)
    panel.image = img

    status.set("Image Loaded")

# ================= CAPACITY =================

def show_capacity():
    if not selected_image:
        return
    img = cv2.imread(selected_image)
    cap = img.shape[0]*img.shape[1]*3//8
    messagebox.showinfo("Capacity", f"Max characters: {cap}")

# ================= PASSWORD STRENGTH =================

def check_password_strength(pwd):
    if len(pwd) < 6:
        return "Weak"
    elif any(c.isdigit() for c in pwd) and any(c.isupper() for c in pwd):
        return "Strong"
    return "Medium"

# ================= ENCODE IMAGE =================

def encode():
    global original_image

    msg = entry_msg.get()
    pwd = simpledialog.askstring("Password", "Enter Password:", show="*")

    if not pwd:
        return

    messagebox.showinfo("Password Strength", check_password_strength(pwd))

    encrypted = encrypt_message(msg, pwd)
    data = text_to_bin(encrypted + "###END###")

    img = original_image.copy()
    edges = cv2.Canny(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY),100,200)

    idx = 0
    for i in range(img.shape[0]):
        for j in range(img.shape[1]):

            if edges[i][j] == 255:
                for k in range(3):
                    if idx < len(data):
                        img[i][j][k] = int(format(img[i][j][k],'08b')[:-1] + data[idx],2)
                        idx += 1
            else:
                if idx < len(data):
                    img[i][j][0] = int(format(img[i][j][0],'08b')[:-1] + data[idx],2)
                    idx += 1

    path = filedialog.asksaveasfilename(defaultextension=".png")
    if path:
        cv2.imwrite(path, img)

        psnr, mse, ssim_val = calculate_metrics(original_image, img)
        messagebox.showinfo("Metrics", f"PSNR:{psnr:.2f}\nMSE:{mse:.2f}\nSSIM:{ssim_val:.4f}")

        show_difference(original_image, img)
        status.set("Encoded Successfully")

# ================= DECODE IMAGE =================

def decode():
    path = filedialog.askopenfilename()
    if not path:
        return

    pwd = simpledialog.askstring("Password","Enter Password:",show="*")
    img = cv2.imread(path)
    edges = cv2.Canny(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY),100,200)

    binary = ""

    for i in range(img.shape[0]):
        for j in range(img.shape[1]):

            if edges[i][j] == 255:
                for k in range(3):
                    binary += format(img[i][j][k],'08b')[-1]
            else:
                binary += format(img[i][j][0],'08b')[-1]

    enc = bin_to_text(binary)
    msg = decrypt_message(enc, pwd)

    if msg is None:
        messagebox.showerror("Error","Wrong Password or No Data")
        return

    text_output.delete("1.0",tk.END)
    text_output.insert(tk.END,msg)
    status.set("Decoded Successfully")

# ================= VIDEO =================

def decode_video():
    path = filedialog.askopenfilename()
    pwd = simpledialog.askstring("Password","Enter Password:",show="*")

    cap = cv2.VideoCapture(path)
    ret, frame = cap.read()

    binary = ""
    for row in frame:
        for pixel in row:
            for i in range(3):
                binary += format(pixel[i],'08b')[-1]

    enc = bin_to_text(binary)
    msg = decrypt_message(enc, pwd)

    text_output.delete("1.0",tk.END)
    text_output.insert(tk.END,msg)
    cap.release()

# ================= AUDIO =================

def decode_audio():
    path = filedialog.askopenfilename(filetypes=[("WAV","*.wav")])
    pwd = simpledialog.askstring("Password","Enter Password:",show="*")

    song = wave.open(path,'rb')
    frames = bytearray(list(song.readframes(song.getnframes())))

    bits = [str(frames[i] & 1) for i in range(len(frames))]
    binary = "".join(bits)

    enc = bin_to_text(binary)
    msg = decrypt_message(enc,pwd)

    text_output.delete("1.0",tk.END)
    text_output.insert(tk.END,msg)
    song.close()

# ================= VISUAL =================

def show_difference(orig, stego):
    diff = cv2.absdiff(orig, stego)
    diff = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX)

    plt.imshow(cv2.cvtColor(diff,cv2.COLOR_BGR2RGB))
    plt.title("Difference")
    plt.show()

def show_histogram():
    img = cv2.imread(selected_image)
    for i,col in enumerate(('b','g','r')):
        hist = cv2.calcHist([img],[i],None,[256],[0,256])
        plt.plot(hist,color=col)
    plt.title("Histogram")
    plt.show()

def detect_stego():
    img = cv2.imread(selected_image)
    lsb = img & 1
    var = np.var(lsb)

    if var < 0.02:
        messagebox.showinfo("Detection","⚠️ Suspicious Image")
    else:
        messagebox.showinfo("Detection","Normal Image")

# ================= UTIL =================

def save_text():
    path = filedialog.asksaveasfilename(defaultextension=".txt")
    with open(path,"w") as f:
        f.write(text_output.get("1.0",tk.END))

def copy_text():
    pyperclip.copy(text_output.get("1.0",tk.END))

def clear_all():
    entry_msg.delete(0,tk.END)
    text_output.delete("1.0",tk.END)
    status.set("Cleared")

# ================= GUI =================

root = tk.Tk()
root.title("🔥 Steganography Pro+")
root.geometry("800x900")

status = tk.StringVar()
status.set("Ready")

tk.Label(root,text="Steganography Pro+",font=("Arial",18,"bold")).pack()

entry_msg = tk.Entry(root,width=60)
entry_msg.pack(pady=5)

def btn(t,c):
    return tk.Button(root,text=t,command=c,width=25,height=2,bg="green",fg="white")

btn("Load Image",load_image).pack()
btn("Check Capacity",show_capacity).pack()
btn("Encode Image",encode).pack()
btn("Decode Image",decode).pack()
btn("Decode Video",decode_video).pack()
btn("Decode Audio",decode_audio).pack()
btn("Histogram",show_histogram).pack()
btn("Detect Stego",detect_stego).pack()
btn("Copy Message",copy_text).pack()
btn("Save Message",save_text).pack()
btn("Clear",clear_all).pack()

panel = tk.Label(root)
panel.pack()

text_output = tk.Text(root,height=6,width=60)
text_output.pack()

tk.Label(root,textvariable=status,bg="black",fg="white").pack(fill="x")

root.mainloop()
