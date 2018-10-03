# Imports
import argparse
import os
import pysrt
import re
import subprocess
import sys
import math

from moviepy.editor import VideoFileClip, TextClip, ImageClip, concatenate_videoclips

from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words

from sumy.summarizers.luhn import LuhnSummarizer
from sumy.summarizers.edmundson import EdmundsonSummarizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.summarizers.text_rank import TextRankSummarizer
from sumy.summarizers.lex_rank import LexRankSummarizer

SUMMARIZERS = {
    'luhn': LuhnSummarizer,
    'edmundson': EdmundsonSummarizer,
    'lsa': LsaSummarizer,
    'text-rank': TextRankSummarizer,
    'lex-rank': LexRankSummarizer
}

def create_summary(filename, regions):
    subclips = []
    input_video = VideoFileClip(filename)
    last_end = 0
    for (start, end) in regions:
        subclip = input_video.subclip(start, end)
        subclips.append(subclip)
        last_end = end
    return concatenate_videoclips(subclips)

def srt_item_to_range(item):
    start_s = item.start.hours*60*60 + item.start.minutes*60 + item.start.seconds + item.start.milliseconds/1000.
    end_s = item.end.hours*60*60 + item.end.minutes*60 + item.end.seconds + item.end.milliseconds/1000.
    return start_s, end_s

def srt_to_doc(srt_file):
    text = ''
    for index, item in enumerate(srt_file):
        if item.text.startswith("["): continue
        text += "(%d) " % index
        text += item.text.replace("\n", "").strip("...").replace(".", "").replace("?", "").replace("!", "")
        text += ". "
    return text

def total_duration_of_regions(regions):
    print(list(map(lambda rangeValue : rangeValue[1]-rangeValue[0] , regions)))
    return sum(list(map(lambda rangeValue : rangeValue[1]-rangeValue[0] , regions)))

def summarize(srt_file, summarizer, n_sentences, language):
    parser = PlaintextParser.from_string(srt_to_doc(srt_file), Tokenizer(language))
    stemmer = Stemmer(language)
    summarizer = SUMMARIZERS[summarizer](stemmer)
    summarizer.stop_words = get_stop_words(language)
    ret = []
    for sentence in summarizer(parser.document, n_sentences):
        index = int(re.findall("\(([0-9]+)\)", str(sentence))[0])
        item = srt_file[index]
        ret.append(srt_item_to_range(item))
    return ret

def find_summary_regions(srt_filename, summarizer="lsa", duration=30, language="english"):
    srt_file = pysrt.open(srt_filename)
    # print(srt_file)
    avg_subtitle_duration = total_duration_of_regions(list(map(srt_item_to_range, srt_file)))/len(srt_file)
    print("The total duration of regions = "+str(total_duration_of_regions(map(srt_item_to_range, srt_file)))+" The total length = "+ str(len(srt_file)))
    print(avg_subtitle_duration)
    n_sentences = duration / avg_subtitle_duration
    summary = summarize(srt_file, summarizer, n_sentences, language)
    total_time = total_duration_of_regions(summary)
    try_higher = total_time < duration
    if try_higher:
        while total_time < duration:
            n_sentences += 1
            summary = summarize(srt_file, summarizer, n_sentences, language)
            total_time = total_duration_of_regions(summary)
    else:
        while total_time > duration:
            n_sentences -= 1
            summary = summarize(srt_file, summarizer, n_sentences, language)
            total_time = total_duration_of_regions(summary)
    return summary


def main():
    print("Enter the video filename")
    video='v.mp4'
    print("Enter the subtitle name ")
    subtitle='sub.srt'
    print("Enter summarizer name ")
    summarizerName='lsa'
    duration=60
    language='english'

    regions = find_summary_regions(subtitle,
                                   summarizer=summarizerName,
                                   duration=duration,
                                   language=language)
    summary = create_summary(video,regions)
    base, ext = os.path.splitext(video)
    dst = "{0}_summarized.mp4".format(base)

    summary.to_videofile(
        dst, 
        codec="libx264", 
        temp_audiofile="temp.m4a",
        remove_temp=True,
        audio_codec="aac",
    )

main()