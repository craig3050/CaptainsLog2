#!/usr/bin/env python
from __future__ import unicode_literals, print_function
import argparse
import sys
import os
import datetime
import shutil

from gcloud import storage

from pydub import AudioSegment

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "DiaryText.json"

parser = argparse.ArgumentParser(description='Convert speech audio to text using Google Speech API')
parser.add_argument('in_filename', help='Input filename (`-` for stdin)')

#user variables
diary_location = "C:/Users/craig/Google Drive/CaptainsLog/Captains_log.txt"
processed_directory = "C:/Users/craig/Google Drive/CaptainsLog/Processed"



def decode_audio(in_filename, **input_kwargs):
    audio = AudioSegment.from_file(in_filename)
    audio = audio.set_frame_rate(16000)
    audio = audio.set_channels(1)
    print(f"Audio Bitrate: {audio.frame_rate}")
    audio.export("converted.flac", format="flac")
    print("Conversion Completed")
    return "converted.flac"


def upload_to_gcs(in_filename):
    # upload resultant file to GCS
    storage_client = storage.Client()
    buckets = list(storage_client.list_buckets())
    bucket = storage_client.get_bucket("audioprocess") # your bucket name
    blob = bucket.blob(in_filename)
    blob.upload_from_filename(in_filename)
    print(f"file uploaded successfully in {buckets}")
    return str("gs://audioprocess/" + in_filename)


def delete_from_gcs(in_filename):
    # upload resultant file to GCS
    storage_client = storage.Client()
    buckets = list(storage_client.list_buckets())
    bucket = storage_client.get_bucket("audioprocess") # your bucket name
    blob = bucket.blob(in_filename)
    blob.delete()
    print(buckets)
    print("File has been deleted")


def speech_recognise(storage_uri):
    from google.cloud import speech_v1
    from google.cloud.speech_v1 import enums

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
    return response


def text_and_confidence_combined(gcs_response):
    text_output = ""  # Blank string for long text document - all parts in one doc
    confidence_total = 0  # Starts the overall confidence total at this point
    confidence_counter = 0  # Starts a counter to which the overall total will be divided
    for result in gcs_response.results:
        # First alternative is the most probable result
        alternative = result.alternatives[0]
        #print(f"Transcript: {alternative.transcript}") #debug lines
        text_output += alternative.transcript
        #print(f"Confidence: {alternative.confidence}") #debug lines
        confidence_total += alternative.confidence
        confidence_counter += 1
    overall_confidence = confidence_total / confidence_counter
    return overall_confidence, text_output


def sentiment_analysis(sentiment_text):
    from google.cloud import language_v1
    from google.cloud.language_v1 import enums

    #Module Setup
    client = language_v1.LanguageServiceClient()
    type_ = enums.Document.Type.PLAIN_TEXT
    language = "en"
    document = {"content": sentiment_text, "type": type_, "language": language}
    encoding_type = enums.EncodingType.UTF8

    #Get overall document sentiment
    response = client.analyze_sentiment(document, encoding_type=encoding_type)
    # Get overall sentiment of the input document
    document_sentiment_score = response.document_sentiment.score
    print(f"Document sentiment score: {document_sentiment_score}")
    document_sentiment_magnitude = response.document_sentiment.magnitude
    print(f"Document sentiment score: {document_sentiment_magnitude}")

    #Interpret the results
    if document_sentiment_score >= 0.2:
        print("Sentiment returned is: Positive")
        return "Positive"
    elif document_sentiment_score == 0.1:
        print("Sentiment returned is: Neutral")
        return "Neutral"
    elif document_sentiment_score == 0.0:
        print("Sentiment returned is: Mixed")
        return "Mixed"
    elif document_sentiment_score <0.0:
        print("Sentiment returned is: Negative")
        return "Negative"


def append_text_to_file(text_list, sentiment):
    #with open automatically closes file after you leave the code block
    with open(diary_location, 'a') as Captains_Log:
        the_date = datetime.datetime.now()
        the_date = the_date.strftime("%d %b %Y")
        confidence = text_list[0]
        text_to_write = text_list[1]
        Captains_Log.write("\n\n\n")
        Captains_Log.write(f"Date: {the_date}, Mood: {sentiment}, Confidence: {confidence} \n")
        Captains_Log.write(text_to_write)


def move_to_processed(file_path):
    destination = processed_directory
    shutil.move(file_path, destination)


if __name__ == '__main__':
    #Get the name of the voice file to transcribe
    args = parser.parse_args()

    #Change the file type and bitrate into the correct format
    print("Converting the file to the correct format...")
    converted_file = decode_audio(args.in_filename)

    #Upload the file to google storage bucket
    print("Uploading the file to Google Storage...")
    file_name = upload_to_gcs(converted_file)

    #Run the speech to text process via google cloud
    print("Running Speech to Text process via Google Cloud...")
    gcs_response = speech_recognise(file_name)

    #Delete the file from GCS
    print("Deleting file from Google Cloud Storage...")
    delete_from_gcs(converted_file)

    #Print the results to the console & append into one long text document
    print("Appending document into one long file...")
    output_text = text_and_confidence_combined(gcs_response)
    print(f"Output Text: {output_text[1]}\n Confidence {output_text[0]}")

    #Sends the text to recognise sentiment
    print("Performing sentiment analysis...")
    overall_sentiment = sentiment_analysis(output_text[1])

    #Writes the text to the top of your overall file
    print("Appending text to your main Diary file...")
    append_text_to_file(output_text, overall_sentiment)

    #Move the converted file into the processed directory
    print ("Moving the file to the processed directory in your Google Drive...")
    move_to_processed(args.in_filename)

    #print a message saying it's all done successfully
    print ("That's all done, go grab a beer!")
    input("press enter to quit")








