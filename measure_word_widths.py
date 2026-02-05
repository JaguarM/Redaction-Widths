import os
from PIL import ImageFont

def main():
    # Configuration
    font_path = "times.ttf"
    input_file = "MyGuesslist.txt"
    output_file = "MyGuesslist_width.txt"
    font_size = 12

    # Load font
    try:
        # Try local directory first
        if os.path.exists(font_path):
            font = ImageFont.truetype(font_path, font_size)
        else:
            # Fallback to system font (Windows)
            font = ImageFont.truetype("times.ttf", font_size)
            print("Local times.ttf not found, using system font.")
    except Exception as e:
        print(f"Error loading font: {e}")
        return

    # Check input file
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    words_data = []

    print("Processing words...")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                word = line.strip()
                if not word:
                    continue
                
                # Calculate width
                # getlength returns the advance width (precise float)
                width = font.getlength(word)
                words_data.append((width, word))
    except Exception as e:
        print(f"Error reading input file: {e}")
        return

    # Sort by width (ascending)
    words_data.sort(key=lambda x: x[0])

    print(f"Writing results to {output_file}...")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for width, word in words_data:
                # Format: width word
                f.write(f"{width} {word}\n")
        print("Done.")
    except Exception as e:
        print(f"Error writing output file: {e}")

if __name__ == "__main__":
    main()
