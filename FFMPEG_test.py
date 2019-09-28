import argparse
import ffmpeg
import sys


parser = argparse.ArgumentParser(description='Convert speech audio to text using Google Speech API')
parser.add_argument('in_filename', help='Input filename (`-` for stdin)')

def main(in_filename, **input_kwargs):
    out, _ = (ffmpeg
              .input(in_filename, **input_kwargs)
              .output('-', format='s16le', acodec='pcm_s16le', ac=1, ar='16k')
              .overwrite_output()
              .run(capture_stdout=True)
              )


if __name__ == '__main__':
    args = parser.parse_args()
    main(args.in_filename)

