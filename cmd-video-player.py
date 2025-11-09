import yt_dlp
import cv2
import os
import time
import threading
from colorama import just_fix_windows_console, Fore, Back, Style
from pygame import mixer
from pynput import keyboard

just_fix_windows_console()

# Global variables for pause control
paused = False
stop_playback = False

def on_key_press(key):
    """Handle keyboard input for pause/resume"""
    global paused, stop_playback
    try:
        if key == keyboard.Key.space:
            paused = not paused
            if paused:
                if audio_available:
                    mixer.music.pause()
            else:
                if audio_available:
                    mixer.music.unpause()
        elif key == keyboard.Key.esc:
            stop_playback = True
            return False  # Stop listener
    except AttributeError:
        pass

# Get YouTube URL from user
print("=" * 50)
print("ASCII YouTube Video Player with Audio")
print("=" * 50)
video_url = input("Enter YouTube video URL: ").strip()

# Validate URL is not empty
if not video_url:
    print("Error: No URL provided!")
    exit()

# Ask for loop option
print("\n" + "=" * 50)
print("Loop Options")
print("=" * 50)
loop_option = input("Do you want to loop the video? (yes/no): ").strip().lower()

loop_count = 0  # 0 means play once
if loop_option in ['yes', 'y']:
    loop_type = input("Enter 'infinite' for continuous loop or number of times to repeat: ").strip().lower()
    if loop_type == 'infinite':
        loop_count = -1  # -1 means infinite loop
        print("Video will loop infinitely. Press ESC to stop.")
    else:
        try:
            loop_count = int(loop_type)
            print(f"Video will play {loop_count + 1} time(s).")
        except ValueError:
            print("Invalid input. Playing once.")
            loop_count = 0
else:
    print("Video will play once.")

# Ask for color option
print("\n" + "=" * 50)
print("Color Options")
print("=" * 50)
color_option = input("Do you want colored ASCII art? (yes/no): ").strip().lower()
use_color = color_option in ['yes', 'y']

if use_color:
    print("Video will be displayed in color.")
else:
    print("Video will be displayed in monochrome.")

# Download the YouTube video with audio
print(f"\nDownloading video from: {video_url}")
print("Please wait...")

ydl_opts = {
    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    'merge_output_format': 'mp4',
    'outtmpl': 'downloaded_video.%(ext)s'
}

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])
except Exception as e:
    print(f"Error downloading video: {e}")
    exit()

print("Download complete! Preparing playback...\n")

# ASCII characters from darkest to brightest
ASCII_CHARS = [' ', '.', ':', '!', '*', 'e', '$', '@', '#']

def rgb_to_ansi256(r, g, b):
    """Convert RGB values to closest ANSI 256 color code"""
    # Use 216 color cube (16-231)
    r_idx = int(r / 255 * 5)
    g_idx = int(g / 255 * 5)
    b_idx = int(b / 255 * 5)
    return 16 + 36 * r_idx + 6 * g_idx + b_idx

def pixel_to_ascii_color(image):
    """Convert image pixels to colored ASCII characters"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    ascii_frame = ''
    height, width = image.shape[:2]
    
    for y in range(height):
        for x in range(width):
            # Get grayscale value for character selection
            pixel_gray = gray[y, x]
            char = ASCII_CHARS[pixel_gray // 32]
            
            if use_color:
                # Get BGR color values
                b, g, r = image[y, x]
                # Convert to ANSI 256 color
                color_code = rgb_to_ansi256(r, g, b)
                # Add ANSI color escape code
                ascii_frame += f'\033[38;5;{color_code}m{char}'
            else:
                ascii_frame += char
        
        ascii_frame += '\033[0m\n'  # Reset color at end of line
    
    return ascii_frame

def format_time(seconds):
    """Format seconds to MM:SS"""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

# Initialize pygame mixer for audio
mixer.init()

# Load audio from video file
try:
    # For MP4 files, we need to extract audio first
    print("Extracting audio...")
    import subprocess
    
    # Extract audio using ffmpeg
    subprocess.run(
        ['ffmpeg', '-y', '-i', 'downloaded_video.mp4', '-vn', '-acodec', 'libmp3lame', '-q:a', '2', 'temp_audio.mp3'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True
    )
    
    mixer.music.load('temp_audio.mp3')
    audio_available = True
    print("Audio extracted successfully!")
except Exception as e:
    print(f"Warning: Could not extract audio: {e}")
    print("Continuing without audio...")
    audio_available = False

# Open the video file
cap = cv2.VideoCapture('downloaded_video.mp4')

if not cap.isOpened():
    print("Error: Could not open video file!")
    exit()

fps = cap.get(cv2.CAP_PROP_FPS)
frame_delay = 1 / fps
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
video_duration = total_frames / fps

# Get terminal dimensions once (reserve 1 line for timer)
terminal_width = os.get_terminal_size().columns
terminal_height = os.get_terminal_size().lines - 2  # Reserve 2 lines for timer

print(f"Playing at {fps} FPS | Terminal size: {terminal_width}x{terminal_height}")
if audio_available:
    print("Audio: Enabled")
else:
    print("Audio: Disabled")

if loop_count == -1:
    print("Loop: Infinite (Press ESC to stop)")
elif loop_count > 0:
    print(f"Loop: {loop_count} time(s)")
else:
    print("Loop: Disabled")

print("\nControls:")
print("  SPACE - Pause/Resume")
print("  ESC - Stop playback")
    
time.sleep(3)  # Give time to read the message

# Start keyboard listener in non-blocking mode
listener = keyboard.Listener(on_press=on_key_press)
listener.start()

# Clear screen
os.system('cls' if os.name == 'nt' else 'clear')

# Play the video with loop support
try:
    current_loop = 0
    keep_playing = True
    
    while keep_playing and not stop_playback:
        # Start audio playback in sync with video
        if audio_available:
            # For looping: -1 = infinite, 0 = once, n = repeat n times
            if loop_count == -1:
                mixer.music.play(-1)  # Play audio infinitely
            elif loop_count > 0 and current_loop == 0:
                mixer.music.play(loop_count)  # Play audio with specified loops
            else:
                mixer.music.play()  # Play once
        
        # Record start time for synchronization
        start_time = time.time()
        frame_count = 0
        pause_start_time = None
        total_pause_duration = 0
        
        # Reset video to beginning
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        # Play video frames
        while cap.isOpened() and not stop_playback:
            if paused:
                if pause_start_time is None:
                    pause_start_time = time.time()
                time.sleep(0.1)
                continue
            else:
                if pause_start_time is not None:
                    total_pause_duration += time.time() - pause_start_time
                    pause_start_time = None
            
            ret, frame = cap.read()
            if not ret:
                break
            
            # Resize frame to terminal size
            frame = cv2.resize(frame, (terminal_width, terminal_height))
            
            # Convert to ASCII
            ascii_frame = pixel_to_ascii_color(frame)
            
            # Calculate current time and total duration
            current_time = (frame_count / fps)
            time_display = f" {format_time(current_time)} / {format_time(video_duration)} "
            
            # Create timer bar with padding to center it
            timer_padding = (terminal_width - len(time_display)) // 2
            timer_line = " " * timer_padding + Style.BRIGHT + Fore.CYAN + time_display + Style.RESET_ALL
            
            # Display timer and frame
            print('\033[H' + timer_line + '\n' + ascii_frame, end='', flush=True)
            
            # Calculate timing for synchronization
            frame_count += 1
            expected_time = start_time + (frame_count * frame_delay) + total_pause_duration
            current_actual_time = time.time()
            sleep_time = expected_time - current_actual_time
            
            # Only sleep if we're ahead of schedule
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        # Check if we should continue looping
        current_loop += 1
        if loop_count == -1:
            # Infinite loop - keep playing
            keep_playing = True
        elif loop_count > 0 and current_loop <= loop_count:
            # Play specified number of times
            keep_playing = True
        else:
            # No more loops
            keep_playing = False

except KeyboardInterrupt:
    print("\n\nPlayback stopped by user (Ctrl+C pressed).")
finally:
    # Stop keyboard listener
    listener.stop()
    
    # Stop audio and unload the music file
    if audio_available:
        mixer.music.stop()
        mixer.music.unload()  # This releases the file lock

# Cleanup
cap.release()
os.system('cls' if os.name == 'nt' else 'clear')
print("Video playback complete!")

# Delete downloaded files
try:
    os.remove('downloaded_video.mp4')
    if audio_available:
        os.remove('temp_audio.mp3')
    print("Temporary files deleted.")
except Exception as e:
    print(f"Could not delete temporary files: {e}")
