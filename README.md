# 🎛️ MasterFlow - AI Audio Mastering

A beautiful, modern web application for AI-powered audio mastering using [Matchering](https://github.com/sergree/matchering).

![MasterFlow Screenshot](https://raw.githubusercontent.com/sergree/matchering/master/images/animation.gif)

## Features

- **Reference Matching**: Match your track's loudness, EQ, and stereo width to any reference song
- **Lightning Fast**: Professional results in under a minute
- **Multiple Formats**: Download in 16-bit or 24-bit WAV
- **Beautiful UI**: Modern, responsive design with smooth animations
- **Drag & Drop**: Easy file uploads with drag and drop support

## Deploy to Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/masterflow)

### Manual Deployment

1. Create a new project on [Railway](https://railway.app)
2. Connect your GitHub repository
3. Railway will automatically detect the configuration and deploy

## Local Development

### Prerequisites

- Python 3.8+
- libsndfile (for audio processing)
- FFmpeg (optional, for MP3 support)

### Installation

```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt update && sudo apt install -y libsndfile1 ffmpeg

# Install Python dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

Visit `http://localhost:5000` in your browser.

## How It Works

1. **Upload Your Track**: The song you want to master
2. **Upload a Reference**: A professionally mastered song with the sound you want
3. **Click Master**: Our AI analyzes both tracks and applies intelligent processing
4. **Download**: Get your mastered track in studio-quality formats

## Tech Stack

- **Backend**: Flask (Python)
- **Audio Processing**: Matchering
- **Frontend**: Vanilla JS with modern CSS
- **Deployment**: Railway with Nixpacks

## Credits

Powered by [Matchering](https://github.com/sergree/matchering) - Open Source Audio Matching and Mastering by Sergree.

## License

GPL-3.0 (same as Matchering)
