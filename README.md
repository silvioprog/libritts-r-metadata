# LibriTTS-R Metadata Generator

Processes the LibriTTS-R speech synthesis dataset and generates a SQLite database schema with books, chapters, speakers, and transcriptions.

## Quick Start

```bash
./run.sh
```

## What it does

- Downloads LibriTTS-R dataset from OpenSLR
- Parses transcription files and metadata
- Generates SQLite database schema
- Converts WAV files to MP3 format

## Requirements

- Python 3.10+
- FFmpeg
- wget
- sqlite3 (for local testing)

## Output

- `dist/01_schema.sql` - Database schema and initial data (books, speakers, chapters)
- `dist/02_transcriptions_*.sql` - Transcription data split into chunks of 650 records
- `dist/03_indexes.sql` - Database indexes for performance optimization
- `dist/` - MP3 audio files (128kbps)

## Local Database Testing

You can test the generated SQL files locally using sqlite3:

```bash
# Import all SQL files into a local database
cat dist/01_schema.sql dist/02_transcriptions_*.sql dist/03_indexes.sql | sqlite3 libritts-r.db

# Verify the data
sqlite3 libritts-r.db "SELECT COUNT(*) FROM transcriptions; SELECT COUNT(*) FROM books; SELECT COUNT(*) FROM chapters; SELECT COUNT(*) FROM speakers;"
```

## Cloudflare Deployment

To deploy to Cloudflare D1 (database) and R2 (audio storage):

```bash
./publish.sh
```

This script will:

1. **Create D1 database** `libritts-r` if it doesn't exist
2. **Execute all SQL files** to populate the database with metadata
3. **Create R2 bucket** `libritts-r` if it doesn't exist  
4. **Upload all MP3 files** to R2, preserving the directory structure

The deployment creates a complete cloud setup with:

- **Structured metadata** in D1 (books, chapters, speakers, transcriptions)
- **Audio files** in R2 (MP3 files organized by dataset subset and chapter)

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
