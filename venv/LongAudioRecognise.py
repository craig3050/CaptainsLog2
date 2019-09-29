#!/usr/bin/env python
from __future__ import unicode_literals, print_function
from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types
import argparse
import sys
import os

from gcloud import storage
from google.cloud import speech_v1
from google.cloud.speech_v1 import enums

from pydub import AudioSegment

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "DiaryText.json"



parser = argparse.ArgumentParser(description='Convert speech audio to text using Google Speech API')
parser.add_argument('in_filename', help='Input filename (`-` for stdin)')


def decode_audio(in_filename, **input_kwargs):
    audio = AudioSegment.from_file(in_filename)
    audio = audio.set_frame_rate(16000)
    audio = audio.set_channels(1)
    print(audio.frame_rate)
    audio.export("converted.flac", format="flac")
    return "converted.flac"


def Upload_to_GCS(in_filename, **input_kwargs):
    # upload resultant file to GCS
    print("Uploading to GCS...")
    storage_client = storage.Client()
    buckets = list(storage_client.list_buckets())
    bucket = storage_client.get_bucket("audioprocess") # your bucket name
    blob = bucket.blob(in_filename)
    blob.upload_from_filename(in_filename)
    print(buckets)
    return str("gs://audioprocess/" + in_filename)

def sample_long_running_recognize(storage_uri):
    client = speech_v1.SpeechClient()
    sample_rate_hertz = 16000

    # The language of the supplied audio
    language_code = "en-gb"

    encoding = enums.RecognitionConfig.AudioEncoding.FLAC
    config = {
        "sample_rate_hertz": sample_rate_hertz,
        "language_code": language_code,
        "encoding": encoding,
    }
    audio = {"uri": storage_uri}

    operation = client.long_running_recognize(config, audio)

    print(u"Waiting for operation to complete...")
    response = operation.result()

    for result in response.results:
        # First alternative is the most probable result
        alternative = result.alternatives[0]
        print(u"Transcript: {}".format(alternative.transcript))


if __name__ == '__main__':
    args = parser.parse_args()
    converted_file = decode_audio(args.in_filename)
    file_name = Upload_to_GCS(converted_file)
    print(file_name)
    sample_long_running_recognize(file_name)



