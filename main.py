import tkinter as tk
from tkinter.filedialog import askopenfilename
from tkinter.constants import NS, Y
from PIL import ImageTk, Image
import cv2
import yt_dlp  # Dùng yt-dlp thay vì pafy
import numpy as np
import time
import os


# Check if running headless
if 'DISPLAY' not in os.environ:
    os.environ['DISPLAY'] = ':99'

# Initialize Tkinter window
try:
    window = tk.Tk()
    window.title("Video Object Detection")
except tk.TclError as e:
    print("Error initializing display. Try running with: xvfb-run python main.py")
    exit(1)


# Define functions first
def openfile():
    filepath = askopenfilename(filetypes=[("Video files", "*.mp4"), ("All files", "*.*")])
    if not filepath:
        return
    txt_edit.delete("1.0", tk.END)
    txt_edit.insert(tk.END, filepath)
    window.title(f"Video Object Detection - {filepath}")


def getlink():
    name = txt_edit.get(1.0, tk.END).strip()
    return name


cap = cv2.VideoCapture()


def videoyoutube():
    try:
        url = getlink()
        if not url: 
            print("No URL entered!")
            return
        print(f"Trying to load video from: {url}")


        # Using yt-dlp to download the video stream
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',  # Try to get best quality
            'noplaylist': True,  # Avoid playlist downloads
            'outtmpl': 'downloaded_video.mp4',  # Output filename
            'quiet': False,  # Set to True to silence output
        }


        # Download the video to the current directory
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            print("Video downloaded successfully!")


        # Now, open the downloaded video
        cap.open('downloaded_video.mp4')  # Open the local downloaded video
        videostream()  # Start the video stream
    except Exception as e:
        print(f"Error loading YouTube video: {e}")


def showvideo():
    cap.open(getlink())
    videostream()


def videostream():
    global frame_id
    starting_time = time.time()
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame.")
        return


    frame_id += 1
    height, width, channels = frame.shape


    blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
    net.setInput(blob)
    outs = net.forward(output_layers)


    class_ids = []
    confidences = []
    boxes = []


    for out in outs:
        for detection in out:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            if confidence > 0.2:
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)


                x = int(center_x - w / 2)
                y = int(center_y - h / 2)


                boxes.append([x, y, w, h])
                confidences.append(float(confidence))
                class_ids.append(class_id)


    indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.8, 0.3)


    d = 0
    for i in range(len(boxes)):
        if i in indexes:
            d += 1
            x, y, w, h = boxes[i]
            label = str(classes[class_ids[i]])
            confidence = confidences[i]
            color = colors[class_ids[i]]
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(frame, label + " " + str(round(confidence, 2)), (x, y + 30),
                        cv2.FONT_HERSHEY_PLAIN, 3, color, 3)


    soluong.delete("1.0", tk.END)
    soluong.insert(tk.END, d)


    elapsed_time = time.time() - starting_time
    fps = frame_id / elapsed_time
    cv2.putText(frame, "FPS: " + str(round(fps, 2)), (10, 50), cv2.FONT_HERSHEY_PLAIN, 4, (0, 0, 0), 3)


    cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
    img = Image.fromarray(cv2image)
    imgtk = ImageTk.PhotoImage(image=img)
    la4.imgtk = imgtk
    la4.configure(image=imgtk)
    la4.after(10, videostream)


# Load YOLO model
net = cv2.dnn.readNet("yolov3.weights", "yolov3.cfg")
with open("coco.names", "r") as f:
    classes = [line.strip() for line in f.readlines()]


layer_names = net.getLayerNames()
output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]


colors = np.random.uniform(0, 255, size=(len(classes), 3))


frame_id = 0


# Frame for text input and file dialog
frame1 = tk.Frame(window, width=500, height=400)
frame1.pack(side=tk.LEFT, padx=10, pady=10)


txt_edit = tk.Text(frame1, padx=5, pady=5, width=40, height=3)  # Adjust size for visibility
txt_edit.pack(fill=tk.X, pady=5)


# Label and Buttons
la1 = tk.Label(frame1, text='Options', padx=8, pady=8, width=20)
la1.pack(fill=tk.X)


la2 = tk.Label(frame1, text='Detected Count', padx=6, pady=6, width=20)
la2.pack(fill=tk.X)


la3 = tk.Label(frame1, text='Enter YouTube URL:', padx=6, pady=6, width=20)
la3.pack(fill=tk.X)


button1 = tk.Button(frame1, width=20, height=1, text='Choose File', pady=5, padx=5, command=openfile)
button1.pack(fill=tk.X, pady=5)


button2 = tk.Button(frame1, width=20, height=1, text='Show Video', pady=5, padx=5, command=showvideo)
button2.pack(fill=tk.X, pady=5)


button3 = tk.Button(frame1, width=20, height=1, text='Show YouTube Video', pady=5, padx=5, command=videoyoutube)
button3.pack(fill=tk.X, pady=5)


soluong = tk.Text(frame1, padx=5, pady=5, width=10, height=1)
soluong.pack(fill=tk.Y, pady=5)


frame2 = tk.Frame(window, width=1000, height=800)
frame2.pack(side=tk.LEFT, padx=10, pady=10)


la2 = tk.Label(frame2, text='Original Video', padx=5, pady=5, width=20)
la2.pack()


la4 = tk.Label(frame2, width=450, height=450)
la4.pack()


window.mainloop()



