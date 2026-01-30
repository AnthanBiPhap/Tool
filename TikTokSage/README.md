# TikTokSage

A modern, user-friendly GUI application for downloading TikTok videos. Built with Python, PySide6, and the TikTokApi library.

## Features

- 📥 **Easy Download**: Simple one-click TikTok video downloads
- 🎵 **Audio Extraction**: Download audio-only from TikTok videos
- 📝 **Metadata Support**: Optionally save video descriptions
- 🌍 **Multi-Language**: Support for English, Spanish, and more
- 💾 **Download History**: Keep track of your downloads
- 🔒 **Proxy Support**: Download with proxy if needed
- 🎨 **Modern UI**: Clean, dark-themed interface similar to YTSage

## Installation

### Requirements
- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install TikTokApi:
   ```bash
   pip install TikTokApi
   ```

4. Run the application:
   ```bash
   python main.py
   ```
   
   Or on Windows, double-click `run_tiktoksage.bat`

## Usage

1. **Enter TikTok URL**: Paste a TikTok video URL in the URL field
2. **Analyze Video**: Click "Analyze" to fetch video information
3. **Choose Options**:
   - Select "Audio Only" if you only want the audio
   - Check "Save Description" to save the video description
4. **Select Download Path**: Choose where to save the video
5. **Download**: Click "Download" to start the download

## Project Structure

```
TikTokSage/
├── main.py                          # Main entry point
├── requirements.txt                 # Python dependencies
├── run_tiktoksage.bat              # Windows launcher
├── LICENSE                          # MIT License
├── README.md                        # This file
├── languages/                       # Language files
│   ├── en.json                     # English
│   └── es.json                     # Spanish
├── assets/
│   └── Icon/                       # Application icon
├── src/
│   ├── __init__.py
│   ├── core/                       # Core functionality
│   │   ├── tiktoksage_downloader.py      # Download logic
│   │   ├── tiktoksage_tiktokapi.py       # TikTokApi wrapper
│   │   └── tiktoksage_utils.py           # Utility functions
│   ├── gui/                        # User Interface
│   │   ├── tiktoksage_gui_main.py        # Main window
│   │   └── tiktoksage_gui_dialogs/      # Dialog windows
│   │       ├── tiktoksage_dialogs_base.py
│   │       ├── tiktoksage_dialogs_custom.py
│   │       ├── tiktoksage_dialogs_settings.py
│   │       ├── tiktoksage_dialogs_history.py
│   │       ├── tiktoksage_dialogs_update.py
│   │       └── tiktoksage_dialogs_selection.py
│   └── utils/                      # Utilities
│       ├── tiktoksage_constants.py       # App constants
│       ├── tiktoksage_logger.py          # Logging
│       ├── tiktoksage_localization.py    # i18n
│       ├── tiktoksage_config_manager.py  # Settings
│       └── tiktoksage_history_manager.py # History
```

## Configuration

Configuration files are stored in the platform-specific directories:

- **Windows**: `%LOCALAPPDATA%/TikTokSage/`
- **macOS**: `~/Library/Application Support/TikTokSage/`
- **Linux**: `~/.local/share/TikTokSage/`

## Troubleshooting

### TikTokApi Installation Issues
If you encounter issues installing TikTokApi, try:
```bash
pip install --upgrade pip
pip install TikTokApi --no-cache-dir
```

### Download Failures
- Ensure the TikTok video URL is valid
- Try adding a proxy if the video is region-restricted
- Check your internet connection

## Building from Source

To create a standalone executable:

```bash
pip install pyinstaller
pyinstaller main.py --windowed --icon=assets/Icon/icon.png --name TikTokSage
```

## Similar Projects

This project was inspired by and follows a similar architecture to [YTSage](https://github.com/yourusername/ytsage), a YouTube downloader with similar features.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for educational purposes only. Ensure you have the right to download content before using this tool. Always respect copyright laws and the terms of service of platforms you're downloading from.

## Support

For issues, questions, or suggestions, please open an issue on the GitHub repository.

---

**Made with ❤️ for the community**
