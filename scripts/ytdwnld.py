import yt_dlp

def download_mp3(youtube_url, output_path, full_video):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': output_path
    }
    
    if not full_video:
        ydl_opts['postprocessor_args'] = ['-t', '15']
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])

# Example usage
# download_mp3('https://www.youtube.com/watch?v=UaHHVNN-z0E', 'output.mp3', full_video=False)
