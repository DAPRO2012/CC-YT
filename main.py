import cv2
import yt_dlp
from flask import Flask, Response, request

app = Flask(__name__)

def generate_frames(video_url):
    # Optimize format query to find a fast, compatible video stream under Render's memory constraints
    ydl_opts = {
        'format': 'bestvideo[height<=360][ext=mp4]/worstvideo[ext=mp4]/best[height<=360]',
        'quiet': True
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            stream_url = info['url']
            
            # Extract YouTube authentication headers so OpenCV isn't blocked
            http_headers = info.get('http_headers', {})
            user_agent = http_headers.get('User-Agent', 'Mozilla/5.0')
    except Exception as e:
        print(f"yt-dlp extraction failed: {e}")
        return

    # Create environment arguments for OpenCV to mimic a real web browser
    # This appends the required User-Agent string to the network request
    opencv_headers = f"User-Agent: {user_agent}\r\n"
    
    # Open the stream with explicit FFmpeg network environment flags
    cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_HW_ACCELERATION, cv2.VIDEO_ACCELERATION_ANY)
    
    # Alternative connection string if standard capture fails on Linux
    if not cap.isOpened():
        # Inject custom HTTP headers directly into the FFmpeg backend handler
        import os
        os.environ["OPENCV_FFMPEG_HTTP_HEADERS"] = opencv_headers
        cap = cv2.VideoCapture(stream_url)

    if not cap.isOpened():
        print("OpenCV failed to open the extracted video stream stream.")
        return

    print("Successfully streaming frames...")
    
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break
        
        # Resize to your low resolution CC target (160x90)
        frame = cv2.resize(frame, (160, 90))
        
        # Encode to JPEG
        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
        if not ret:
            continue
            
        frame_bytes = buffer.tobytes()
        
        # Send 4-byte header size + raw image bytes
        yield len(frame_bytes).to_bytes(4, byteorder='big') + frame_bytes
        
    cap.release()

@app.route('/video')
def video_stream():
    video_url = request.args.get('url', 'https://youtube.com')
    return Response(generate_frames(video_url), mimetype='application/octet-stream')
