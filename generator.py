import os
import sys
import glob
import subprocess
from datetime import datetime
from tqdm import tqdm

DIST_DIR = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else "dist"
TMP_DIR = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else "tmp"


def parse_transcriptions():
    trans_files = glob.glob(f"{TMP_DIR}/LibriTTS_R/*/*/*/*.trans.tsv")
    transcriptions = []
    valid_chapter_ids = set()
    for trans_file in trans_files:
        with open(trans_file, "r") as f:
            for line in f:
                parts = line.split("\t")
                ids = parts[0].strip().split("_")
                chapter_id = ids[1].strip()
                segment = ids[2].strip()
                subsegment = ids[3].strip()
                transcript = parts[1].strip()
                valid_chapter_ids.add(chapter_id)
                transcriptions.append((chapter_id, segment, subsegment, transcript))
    return transcriptions, valid_chapter_ids


def parse_books():
    books = []
    with open(f"{TMP_DIR}/LibriTTS_R/BOOKS.txt", "r") as f:
        content = f.read()
        rounds = 0
        token = ""
        id = ""
        title = ""
        author = ""
        for char in content:
            if char == "|":
                if rounds == 0:
                    id = token.strip()
                elif rounds == 1:
                    title_lines = token.split("\n")
                    if len(title_lines) > 1:
                        title = " / ".join(map(lambda x: x.strip(), title_lines))
                    else:
                        title = title_lines[0].strip()
                rounds += 1
                token = ""
            else:
                if char == "\n" and rounds == 2:
                    author = token.strip()
                    books.append((id, title, author))
                    rounds = 0
                    token = ""
                else:
                    token += char
    return books


def parse_chapters(valid_chapter_ids, existing_book_ids):
    chapters = []
    valid_book_ids = set()
    valid_speaker_ids = set()
    with open(f"{TMP_DIR}/LibriTTS_R/CHAPTERS.txt", "r") as f:
        for line in f:
            if line and not line.startswith(";"):
                parts = line.split("|")
                id = parts[0].strip()
                if id in valid_chapter_ids:
                    book_id = parts[5].strip()
                    if book_id in existing_book_ids:
                        speaker_id = parts[1].strip()
                        minutes = parts[2].strip()
                        subset = parts[3].strip()
                        title = parts[6].strip()
                        valid_book_ids.add(book_id)
                        valid_speaker_ids.add(speaker_id)
                        chapters.append(
                            (id, book_id, speaker_id, title, minutes, subset)
                        )
    return chapters, valid_book_ids, valid_speaker_ids


def parse_speakers(valid_speaker_ids):
    speakers = []
    with open(f"{TMP_DIR}/LibriTTS_R/speakers.tsv", "r") as f:
        next(f)
        for line in f:
            parts = line.split("\t")
            id = parts[0].strip()
            if id in valid_speaker_ids:
                gender = parts[1].strip()
                name = parts[3].strip()
                speakers.append((id, name, gender))
    return speakers


def generate_sql():
    existing_transcriptions, valid_chapter_ids = parse_transcriptions()
    existing_books = parse_books()
    existing_book_ids = {book[0] for book in existing_books}
    chapters, valid_book_ids, valid_speaker_ids = parse_chapters(
        valid_chapter_ids, existing_book_ids
    )
    books = [book for book in existing_books if book[0] in valid_book_ids]
    speakers = parse_speakers(valid_speaker_ids)
    transcriptions = [
        transcription
        for transcription in existing_transcriptions
        if transcription[0] in [chapter[0] for chapter in chapters]
    ]

    schema_content = []
    schema_content.append("-- -- LibriTTS-R Database Schema")
    schema_content.append("-- Generated on: " + datetime.now().strftime("%Y-%m-%d"))
    schema_content.append("")

    schema_content.append("PRAGMA foreign_keys = ON;")
    schema_content.append("")

    schema_content.append("-- Create books table")
    schema_content.append("CREATE TABLE books (")
    schema_content.append("  id INTEGER PRIMARY KEY,")
    schema_content.append("  title TEXT NOT NULL,")
    schema_content.append("  author TEXT")
    schema_content.append(");")
    schema_content.append("")

    schema_content.append("-- Create speakers table")
    schema_content.append("CREATE TABLE speakers (")
    schema_content.append("  id INTEGER PRIMARY KEY,")
    schema_content.append("  name TEXT NOT NULL,")
    schema_content.append("  gender TEXT NOT NULL")
    schema_content.append(");")
    schema_content.append("")

    schema_content.append("-- Create chapters table")
    schema_content.append("CREATE TABLE chapters (")
    schema_content.append("  id INTEGER PRIMARY KEY,")
    schema_content.append("  book_id INTEGER NOT NULL,")
    schema_content.append("  speaker_id INTEGER NOT NULL,")
    schema_content.append("  title TEXT NOT NULL,")
    schema_content.append("  minutes REAL NOT NULL,")
    schema_content.append("  subset TEXT NOT NULL,")
    schema_content.append("  FOREIGN KEY (book_id) REFERENCES books(id),")
    schema_content.append("  FOREIGN KEY (speaker_id) REFERENCES speakers(id)")
    schema_content.append(");")
    schema_content.append("")

    schema_content.append("-- Create transcriptions table")
    schema_content.append("CREATE TABLE transcriptions (")
    schema_content.append("  chapter_id INTEGER NOT NULL,")
    schema_content.append("  segment TEXT NOT NULL,")
    schema_content.append("  subsegment TEXT NOT NULL,")
    schema_content.append("  transcript TEXT NOT NULL,")
    schema_content.append("  PRIMARY KEY (chapter_id, segment, subsegment),")
    schema_content.append("  FOREIGN KEY (chapter_id) REFERENCES chapters(id)")
    schema_content.append(");")
    schema_content.append("")

    schema_content.append("-- Insert books data")
    book_values = []
    for id, title, author in books:
        id_value = int(id)
        title_value = title.replace("'", "''")
        author_value = f"'{author.replace("'", "''")}'" if author else "NULL"
        book_values.append(f"({id_value}, '{title_value}', {author_value})")
    schema_content.append("INSERT INTO books (id, title, author)")
    schema_content.append("VALUES")
    schema_content.append("  " + ",\n  ".join(book_values) + ";")
    schema_content.append("")

    schema_content.append("-- Insert speakers data")
    speaker_values = []
    for id, name, gender in speakers:
        id_value = int(id)
        name_value = name.replace("'", "''")
        gender_value = gender.replace("'", "''")
        speaker_values.append(f"({id_value}, '{name_value}', '{gender_value}')")
    schema_content.append("INSERT INTO speakers (id, name, gender)")
    schema_content.append("VALUES")
    schema_content.append("  " + ",\n  ".join(speaker_values) + ";")
    schema_content.append("")

    schema_content.append("-- Insert chapters data")
    chapter_values = []
    for id, book_id, speaker_id, title, minutes, subset in chapters:
        id_value = int(id)
        book_id_value = int(book_id)
        speaker_id_value = int(speaker_id)
        title_value = title.replace("'", "''")
        minutes_value = float(minutes)
        subset_value = subset.replace("'", "''")
        chapter_values.append(
            f"({id_value}, {book_id_value}, {speaker_id_value}, '{title_value}', {minutes_value}, '{subset_value}')"
        )
    schema_content.append(
        "INSERT INTO chapters (id, book_id, speaker_id, title, minutes, subset)"
    )
    schema_content.append("VALUES")
    schema_content.append("  " + ",\n  ".join(chapter_values) + ";")
    schema_content.append("")

    with open(f"{DIST_DIR}/01_schema.sql", "w") as f:
        f.write("\n".join(schema_content))

    chunk_size = 650
    transcription_chunks = [
        transcriptions[i : i + chunk_size]
        for i in range(0, len(transcriptions), chunk_size)
    ]

    for i, chunk in enumerate(transcription_chunks):
        chunk_content = []
        chunk_content.append(
            f"-- -- Transcription chunk {i+1} of {len(transcription_chunks)}"
        )
        chunk_content.append(f"-- Generated on: {datetime.now().strftime('%Y-%m-%d')}")
        chunk_content.append("")

        chunk_content.append("-- Insert transcriptions data")
        transcription_values = []
        for chapter_id, segment, subsegment, transcript in chunk:
            chapter_id_value = int(chapter_id)
            segment_value = segment
            subsegment_value = subsegment
            transcript_value = transcript.replace("'", "''")
            transcription_values.append(
                f"({chapter_id_value}, '{segment_value}', '{subsegment_value}', '{transcript_value}')"
            )
        chunk_content.append(
            "INSERT INTO transcriptions (chapter_id, segment, subsegment, transcript)"
        )
        chunk_content.append("VALUES")
        chunk_content.append("  " + ",\n  ".join(transcription_values) + ";")
        chunk_content.append("")

        with open(f"{DIST_DIR}/02_transcriptions_{i+1:02d}.sql", "w") as f:
            f.write("\n".join(chunk_content))

    indexes_content = []
    indexes_content.append("-- -- Indexes for LibriTTS-R Database")
    indexes_content.append("-- Generated on: " + datetime.now().strftime("%Y-%m-%d"))
    indexes_content.append("")

    indexes_content.append("-- Book search optimization")
    indexes_content.append(
        "CREATE INDEX idx_books_title_nocase ON books(title COLLATE NOCASE);"
    )
    indexes_content.append(
        "CREATE INDEX idx_books_author_nocase ON books(author COLLATE NOCASE);"
    )
    indexes_content.append("")

    indexes_content.append("-- Chapter and speaker search optimization")
    indexes_content.append("CREATE INDEX idx_chapters_book_id ON chapters(book_id);")
    indexes_content.append(
        "CREATE INDEX idx_chapters_speaker_id ON chapters(speaker_id);"
    )
    indexes_content.append(
        "CREATE INDEX idx_chapters_book_speaker ON chapters(book_id, speaker_id);"
    )
    indexes_content.append("")

    indexes_content.append("-- Transcript search optimization")
    indexes_content.append(
        "CREATE INDEX idx_transcriptions_chapter_id ON transcriptions(chapter_id);"
    )
    indexes_content.append(
        "CREATE INDEX idx_transcriptions_transcript_nocase ON transcriptions(transcript COLLATE NOCASE);"
    )
    indexes_content.append(
        "CREATE INDEX idx_transcriptions_segment_order ON transcriptions(chapter_id, segment, subsegment);"
    )
    indexes_content.append("")

    with open(f"{DIST_DIR}/03_indexes.sql", "w") as f:
        f.write("\n".join(indexes_content))

    return transcriptions


def convert_to_mp3(transcriptions):
    base_dir = f"{TMP_DIR}/LibriTTS_R"
    existing_wav_files = glob.glob(f"{base_dir}/*/*/*/*.wav")
    wav_files = [
        wav_file
        for wav_file in existing_wav_files
        if wav_file.split("/")[-2]
        in [transcription[0] for transcription in transcriptions]
    ]
    for wav_file in tqdm(wav_files, desc="Converting WAV files to MP3", unit="file"):
        mp3_file = f"{DIST_DIR}/{wav_file[len(base_dir)+1:-4]}.mp3"
        os.makedirs(os.path.dirname(mp3_file), exist_ok=True)
        subprocess.run(
            [
                "ffmpeg",
                "-i",
                wav_file,
                "-loglevel",
                "error",
                "-codec:a",
                "mp3",
                "-q:a",
                "4",
                "-y",
                mp3_file,
            ]
        )


if __name__ == "__main__":
    transcriptions = generate_sql()
    convert_to_mp3(transcriptions)
