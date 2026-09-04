import cv2
import yt_dlp
from flask import Flask, Response, request

app = Flask(__name__)

def generate_frames(video_url):
    # Force yt-dlp to grab a lower quality stream to stay within Render's 512MB RAM limit
    ydl_opts = {'format': 'worstvideo[ext=mp4]/bestvideo[height<=360]'}
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            stream_url = info['url']
    except Exception as e:
        print(f"Error fetching YouTube URL: {e}")
        return

    cap = cv2.VideoCapture(stream_url)
    
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break
        
        # Keep resolution low (e.g., 160x90) so it doesn't max out Render's CPU/RAM
        frame = cv2.resize(frame, (160, 90))
        
        # Compress frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
        if not ret:
            continue
            
        frame_bytes = buffer.tobytes()
        
        # Send 4-byte header size followed by raw frame data
        yield len(frame_bytes).to_bytes(4, byteorder='big') + frame_bytes
        
    cap.release()

@app.route('/video')
def video_stream():
    # Allows you to pass any youtube link dynamically from Minecraft!
    # Example: http://onrender.com
    video_url = request.args.get('url', 'https://youtube.com')
    return Response(generate_frames(video_url), mimetype='application/octet-stream')
