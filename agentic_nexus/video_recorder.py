import os
import subprocess
import threading
import time
from datetime import datetime
from pynput import keyboard as pynput_keyboard
import mss
import cv2
import numpy as np

RECORDINGS_DIR = 'recordings'
FFMPEG_PATH = 'ffmpeg'  # Assumes ffmpeg is in PATH
VIDEO_DEVICE = '0'  # Default webcam
AUDIO_DEVICE = 'default'  # Default microphone (may need adjustment per OS)

class VideoRecorder:
    def __init__(self):
        os.makedirs(RECORDINGS_DIR, exist_ok=True)
        self.recording_process = None
        self.screen_recording_thread = None
        self.screen_recording_stop = threading.Event()
        self.recording = False
        self.current_timestamp = None

    def get_output_filename(self, suffix):
        timestamp = self.current_timestamp or datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        # Store the screen recording as .avi initially, then convert to .mp4 later
        extension = '.mp4'
        if suffix == '_screen':
            # For internal use, to be converted later
            self._screen_avi_path = os.path.join(RECORDINGS_DIR, f'recording_{timestamp}{suffix}.avi')
            # Final MP4 path for Gemini compatibility
            return os.path.join(RECORDINGS_DIR, f'recording_{timestamp}{suffix}{extension}')
        else:
            return os.path.join(RECORDINGS_DIR, f'recording_{timestamp}{suffix}{extension}')

    def start(self):
        if self.recording:
            print('Already recording.')
            return
        self.current_timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        output_file = self.get_output_filename('')
        screen_file = self.get_output_filename('_screen')
        print(f'Starting recording: {output_file} and {screen_file}')
        
        try:
            # Start webcam/mic recording
            time.sleep(0.2)  # Add a small delay in case the device was just released
            cmd = [
                FFMPEG_PATH,
                '-y',
                '-f', 'v4l2', '-i', f'/dev/video{VIDEO_DEVICE}',  # Linux webcam
                '-f', 'alsa', '-i', AUDIO_DEVICE,                # Linux audio
                '-vcodec', 'libx264', '-preset', 'ultrafast',
                '-acodec', 'aac',
                output_file
            ]
            try:
                self.recording_process = subprocess.Popen(cmd, stderr=subprocess.PIPE)
                # Check immediately if there was an error starting the process
                time.sleep(0.5)
                if self.recording_process.poll() is not None:
                    stderr_output = self.recording_process.stderr.read().decode('utf-8')
                    if 'Device or resource busy' in stderr_output:
                        print("Warning: Webcam is busy. Recording screen only.")
                        self.recording_process = None
                    else:
                        print(f"Warning: FFmpeg process exited with error: {stderr_output}")
                        self.recording_process = None
            except Exception as e:
                print(f"Error starting webcam recording: {e}")
                self.recording_process = None
                
            # Start screen recording in a thread
            self.screen_recording_stop.clear()
            self.screen_recording_thread = threading.Thread(target=self.record_screen, args=(screen_file, self.screen_recording_stop))
            self.screen_recording_thread.start()
            self.recording = True
        except Exception as e:
            print(f"Error starting recording: {e}")
            self.stop()

    def stop(self):
        if not self.recording:
            print('Not currently recording.')
            return
        print('Stopping recording.')
        if self.recording_process:
            self.recording_process.terminate()
            self.recording_process.wait()
        # Stop screen recording
        self.screen_recording_stop.set()
        if self.screen_recording_thread:
            self.screen_recording_thread.join()
            
        # Convert screen recording from AVI to MP4 if it exists
        if hasattr(self, '_screen_avi_path') and os.path.exists(self._screen_avi_path):
            screen_mp4_file = self.get_output_filename('_screen')
            print(f"Converting screen recording to MP4 format...")
            try:
                # Convert AVI to MP4 using ffmpeg
                cmd = [
                    FFMPEG_PATH,
                    '-y',
                    '-i', self._screen_avi_path,
                    '-c:v', 'libx264',
                    '-preset', 'fast',
                    '-crf', '23',
                    screen_mp4_file
                ]
                conversion_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = conversion_process.communicate()
                
                if conversion_process.returncode == 0:
                    print(f"Successfully converted to MP4: {screen_mp4_file}")
                    # Remove the temporary AVI file
                    os.remove(self._screen_avi_path)
                else:
                    print(f"Error converting to MP4: {stderr.decode('utf-8')}")
            except Exception as e:
                print(f"Failed to convert screen recording to MP4: {e}")
        
        self.recording = False
        self.current_timestamp = None

    def toggle(self):
        if not self.recording:
            self.start()
        else:
            self.stop()
        time.sleep(0.5)  # Debounce

    def record_screen(self, filename, stop_event):
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]  # Primary monitor
                # Use XVID codec with .avi format for maximum compatibility
                try:
                    fourcc = cv2.VideoWriter_fourcc(*'XVID')
                    fps = 15
                    width = monitor['width']
                    height = monitor['height']
                    # Use the temporary AVI path instead of the final MP4 path
                    out = cv2.VideoWriter(self._screen_avi_path, fourcc, fps, (width, height))
                    if not out.isOpened():
                        raise ValueError('XVID VideoWriter failed to open')
                except Exception as e:
                    print(f"Failed to initialize VideoWriter: {e}")
                    # Fallback to using ffmpeg directly
                    print("Trying fallback method with ffmpeg...")
                    return self.fallback_screen_record(filename, stop_event)
                
                last_time = time.time()
                while not stop_event.is_set():
                    img = np.array(sct.grab(monitor))
                    frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                    out.write(frame)
                    # Maintain FPS
                    elapsed = time.time() - last_time
                    sleep_time = max(0, (1.0 / fps) - elapsed)
                    time.sleep(sleep_time)
                    last_time = time.time()
                out.release()
            # Check file size
            if os.path.exists(self._screen_avi_path) and os.path.getsize(self._screen_avi_path) < 1024:
                print(f"Warning: Screen recording file {self._screen_avi_path} is very small or empty.")
        except Exception as e:
            print(f"Screen recording error: {e}")

    def fallback_screen_record(self, filename, stop_event):
        """Fallback to using ffmpeg for screen recording if OpenCV fails"""
        try:
            # Create a temporary script to capture screen with ffmpeg
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                width = monitor["width"]
                height = monitor["height"]
                
                # Start ffmpeg process to record screen
                cmd = [
                    FFMPEG_PATH,
                    '-y',
                    '-f', 'x11grab',  # X11 display grabbing
                    '-s', f'{width}x{height}',  # Screen size
                    '-i', ':0.0',  # Display to capture
                    '-r', '15',  # Frame rate
                    '-vcodec', 'libx264',
                    '-preset', 'ultrafast',
                    self._screen_avi_path
                ]
                
                ffmpeg_process = subprocess.Popen(cmd)
                
                # Wait until stop event is set
                while not stop_event.is_set():
                    time.sleep(0.5)
                    # Check if ffmpeg process is still running
                    if ffmpeg_process.poll() is not None:
                        print("Warning: ffmpeg screen recording process exited unexpectedly")
                        break
                
                # Terminate the ffmpeg process
                if ffmpeg_process.poll() is None:
                    ffmpeg_process.terminate()
                    ffmpeg_process.wait()
                
                # Check file size
                if os.path.exists(self._screen_avi_path) and os.path.getsize(self._screen_avi_path) < 1024:
                    print(f"Warning: Screen recording file {self._screen_avi_path} is very small or empty.")
                    
        except Exception as e:
            print(f"Fallback screen recording error: {e}")

    def hotkey_listener(self):
        print('Press F9 to start/stop recording.')
        def on_press(key):
            try:
                if key == pynput_keyboard.Key.f9:
                    self.toggle()
            except AttributeError:
                pass
        with pynput_keyboard.Listener(on_press=on_press) as listener:
            listener.join()

    def run(self):
        listener_thread = threading.Thread(target=self.hotkey_listener, daemon=True)
        listener_thread.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            if self.recording:
                self.stop()
            print('Exiting.')

def main():
    recorder = VideoRecorder()
    recorder.run()

if __name__ == '__main__':
    main() 