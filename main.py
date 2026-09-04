import base64
import os
import cv2
import yt_dlp
from flask import Flask, Response, request

app = Flask(__name__)

def generate_frames(video_url):
    ydl_opts = {
        'format': 'bestvideo[height<=360][ext=mp4]/worstvideo[ext=mp4]/best[height<=360]',
        'quiet': True,
        # Spoof the client to bypass YouTube's datacenter bot detection
        'extractor_args': {
            'youtube': {
                'player_client': ['web_safari', 'android']
            }
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            stream_url = info['url']
            
            http_headers = info.get('http_headers', {})
            user_agent = http_headers.get('User-Agent', 'Mozilla/5.0')
    except Exception as e:
        print(f"yt-dlp extraction failed: {e}")
        yield b'YTDL' + b'_ERROR'.ljust(10, b' ')
        return

    opencv_headers = f"User-Agent: {user_agent}\r\n"
    os.environ["OPENCV_FFMPEG_HTTP_HEADERS"] = opencv_headers
    
    cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        cap = cv2.VideoCapture(stream_url)

    if not cap.isOpened():
        print("OpenCV failed to open the extracted video stream.")
        yield b'OPEN' + b'_ERROR'.ljust(10, b' ')
        return

    print("Successfully streaming frames...")
    
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break
        
        frame = cv2.resize(frame, (160, 90))
        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
        
        if not ret:
            continue
            
        frame_bytes = buffer.tobytes()
        b64_bytes = base64.b64encode(frame_bytes)
        
        yield len(b64_bytes).to_bytes(4, byteorder='big') + b64_bytes
        
    cap.release()

@app.route('/video')
def video_stream():
    video_url = request.args.get('url', 'https://www.youtube.com/watch?v=dQw4w9WgXcQ')
    return Response(generate_frames(video_url), mimetype='application/octet-stream')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
