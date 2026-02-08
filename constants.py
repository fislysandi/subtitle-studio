"""
Constants for Subtitle Studio
"""

# =============================================================================
# Languages (Whisper supported)
# =============================================================================

LANGUAGES = {
    "auto": "Auto-detect",
    "en": "English",
    "zh": "Chinese",
    "de": "German",
    "es": "Spanish",
    "ru": "Russian",
    "ko": "Korean",
    "fr": "French",
    "ja": "Japanese",
    "pt": "Portuguese",
    "tr": "Turkish",
    "pl": "Polish",
    "ca": "Catalan",
    "nl": "Dutch",
    "ar": "Arabic",
    "sv": "Swedish",
    "it": "Italian",
    "id": "Indonesian",
    "hi": "Hindi",
    "fi": "Finnish",
    "vi": "Vietnamese",
    "he": "Hebrew",
    "uk": "Ukrainian",
    "el": "Greek",
    "ms": "Malay",
    "cs": "Czech",
    "ro": "Romanian",
    "da": "Danish",
    "hu": "Hungarian",
    "ta": "Tamil",
    "no": "Norwegian",
    "th": "Thai",
    "ur": "Urdu",
    "hr": "Croatian",
    "bg": "Bulgarian",
    "lt": "Lithuanian",
    "la": "Latin",
    "mi": "Maori",
    "ml": "Malayalam",
    "cy": "Welsh",
    "sk": "Slovak",
    "te": "Telugu",
    "fa": "Persian",
    "lv": "Latvian",
    "bn": "Bengali",
    "sr": "Serbian",
    "az": "Azerbaijani",
    "sl": "Slovenian",
    "kn": "Kannada",
    "et": "Estonian",
    "mk": "Macedonian",
    "br": "Breton",
    "eu": "Basque",
    "is": "Icelandic",
    "hy": "Armenian",
    "ne": "Nepali",
    "mn": "Mongolian",
    "bs": "Bosnian",
    "kk": "Kazakh",
    "sq": "Albanian",
    "sw": "Swahili",
    "gl": "Galician",
    "mr": "Marathi",
    "pa": "Punjabi",
    "si": "Sinhala",
    "km": "Khmer",
    "sn": "Shona",
    "yo": "Yoruba",
    "so": "Somali",
    "af": "Afrikaans",
    "oc": "Occitan",
    "ka": "Georgian",
    "be": "Belarusian",
    "tg": "Tajik",
    "sd": "Sindhi",
    "gu": "Gujarati",
    "am": "Amharic",
    "yi": "Yiddish",
    "lo": "Lao",
    "uz": "Uzbek",
    "fo": "Faroese",
    "ht": "Haitian Creole",
    "ps": "Pashto",
    "tk": "Turkmen",
    "nn": "Nynorsk",
    "mt": "Maltese",
    "sa": "Sanskrit",
    "lb": "Luxembourgish",
    "my": "Myanmar",
    "bo": "Tibetan",
    "tl": "Tagalog",
    "mg": "Malagasy",
    "as": "Assamese",
    "tt": "Tatar",
    "haw": "Hawaiian",
    "ln": "Lingala",
    "ha": "Hausa",
    "ba": "Bashkir",
    "jw": "Javanese",
    "su": "Sundanese",
}

# Create enum items for Blender
LANGUAGE_ITEMS = [
    (code, name, f"Transcribe in {name}") for code, name in LANGUAGES.items()
]

# =============================================================================
# Whisper Models
# =============================================================================

MODELS = {
    "tiny": {
        "name": "Tiny",
        "description": "Fastest, lowest accuracy (39 MB)",
        "size": "39 MB",
    },
    "base": {
        "name": "Base",
        "description": "Fast, good accuracy (74 MB)",
        "size": "74 MB",
    },
    "small": {
        "name": "Small",
        "description": "Balanced speed/accuracy (244 MB)",
        "size": "244 MB",
    },
    "medium": {
        "name": "Medium",
        "description": "Slow, high accuracy (769 MB)",
        "size": "769 MB",
    },
    "large-v3": {
        "name": "Large v3",
        "description": "Slowest, best accuracy (1.5 GB)",
        "size": "1.5 GB",
    },
}

MODEL_ITEMS = [
    (key, info["name"], f"{info['description']}") for key, info in MODELS.items()
]

# =============================================================================
# Subtitle Formats
# =============================================================================

SUBTITLE_FORMATS = {
    ".srt": {
        "name": "SubRip",
        "description": "Standard subtitle format",
        "extensions": [".srt"],
    },
    ".vtt": {
        "name": "WebVTT",
        "description": "Web Video Text Tracks",
        "extensions": [".vtt", ".webvtt"],
    },
    ".ass": {
        "name": "Advanced SubStation Alpha",
        "description": "Advanced styling support",
        "extensions": [".ass", ".ssa"],
    },
    ".ssa": {
        "name": "SubStation Alpha",
        "description": "Legacy ASS format",
        "extensions": [".ssa"],
    },
}

# =============================================================================
# Import/Export Settings
# =============================================================================

IMPORT_EXPORT_FORMATS = [
    (".srt", "SubRip (.srt)", "Import/Export SubRip format"),
    (".vtt", "WebVTT (.vtt)", "Import/Export WebVTT format"),
    (".ass", "Advanced SSA (.ass)", "Import/Export ASS format"),
    (".ssa", "SubStation Alpha (.ssa)", "Import/Export SSA format"),
]

# =============================================================================
# UI Constants
# =============================================================================

PANEL_CATEGORY = "Subtitle Studio"
DEFAULT_FONT_SIZE = 24
DEFAULT_FONT_PATH = None  # Use Blender default

# =============================================================================
# File Paths
# =============================================================================

DEPENDENCIES_DIR = "libs"
MODELS_DIR = "models"
TEMP_DIR = "temp"

# =============================================================================
# Transcription Settings
# =============================================================================

DEFAULT_BEAM_SIZE = 5
DEFAULT_BEST_OF = 5
DEFAULT_TEMPERATURE = 0.0
DEFAULT_COMPRESSION_RATIO_THRESHOLD = 2.4
DEFAULT_VAD_FILTER = True
