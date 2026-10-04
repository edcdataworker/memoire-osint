"""Encode real browser captures, preserving scene durations and cutting gaps."""
import argparse
import json
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def clock(seconds):
    hundredths = round(seconds * 100)
    return f"{hundredths // 360000}:{hundredths // 6000 % 60:02}:{hundredths // 100 % 60:02}.{hundredths % 100:02}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    frames = sorted(json.loads((args.capture / "frames.json").read_text()), key=lambda f: f["timestamp"])
    clips = json.loads((args.capture / "clips.json").read_text())
    concat = ["ffconcat version 1.0"]
    subtitles = ["[Script Info]", "ScriptType: v4.00+", "PlayResX: 1600", "PlayResY: 1000", "[V4+ Styles]", "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding", "Style: Caption,Arial,30,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,2,30,30,35,1", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    offset = 0
    rendered = args.capture / "captioned"
    rendered.mkdir(exist_ok=True)
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 30)
    for clip_number, clip in enumerate(clips):
        begin, end = clip["begin"] / 1000, clip["end"] / 1000
        previous = [f for f in frames if f["timestamp"] <= begin]
        assert previous, "Missing initial frame"
        selected = [(begin, previous[-1])] + [(f["timestamp"], f) for f in frames if begin < f["timestamp"] < end]
        for i, (when, frame) in enumerate(selected):
            until = selected[i + 1][0] if i + 1 < len(selected) else end
            target = rendered / f"{clip_number:02}_{Path(frame['path']).name}"
            if not target.exists():
                canvas = Image.new("RGB", (1600, 1000), "#102330")
                with Image.open(frame["path"]) as raw:
                    canvas.paste(raw.resize((1600, 900)), (0, 0))
                ImageDraw.Draw(canvas).text((800, 950), clip["label"], anchor="mm", fill="white", font=font)
                canvas.save(target, quality=92)
            path = str(target).replace("'", "'\\''")
            concat.extend([f"file '{path}'", f"duration {until - when:.6f}"])
        duration = end - begin
        subtitles.append(f"Dialogue: 0,{clock(offset)},{clock(offset + duration)},Caption,,0,0,0,,{clip['label']}")
        offset += duration
    concat.append(concat[-2])
    (args.capture / "timeline.ffconcat").write_text("\n".join(concat) + "\n")
    (args.capture / "captions.ass").write_text("\n".join(subtitles) + "\n")
    subprocess.run(["ffmpeg", "-y", "-v", "warning", "-f", "concat", "-safe", "0", "-i", str(args.capture / "timeline.ffconcat"), "-r", "25", "-c:v", "libx264", "-crf", "21", "-preset", "fast", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(args.output)], check=True)
    print(json.dumps({"duration_s": offset, "scenes": len(clips), "source_frames": len(frames)}))


if __name__ == "__main__":
    main()
