from gensim.summarization import *
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import textwrap
import sys
import tweepy
import time
import re
from _constant import *
import scrapy
import json
from scrapy.crawler import CrawlerProcess
from twisted.internet import reactor
from urllib.request import urlopen
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
from twisted.internet import reactor

print('Welcome to Ringkas Berita!!', flush=True)

auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)
api = tweepy.API(auth, wait_on_rate_limit=True)

FILE_NAME = 'last_seen_id.txt'

def retrieve_last_seen_id(file_name):
    f_read = open(file_name, 'r')
    last_seen_id = int(f_read.read().strip())
    f_read.close()
    return last_seen_id

def store_last_seen_id(last_seen_id, file_name):
    f_write = open(file_name, 'w')
    f_write.write(str(last_seen_id))
    f_write.close()
    return

def take_link():
    print('retrieving tweets...', flush=True)
    last_seen_id = retrieve_last_seen_id(FILE_NAME)
    mentions = api.mentions_timeline(last_seen_id, tweet_mode='extended')
    for mention in reversed(mentions):
        last_seen_id = mention.id
        if 'https://' in mention.full_text.lower():
            urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', mention.full_text)
            print('found URL!', flush=True)
            print(mention.id, flush=True)
            print('responding back...', flush=True)
            print(urls, flush=True)
            return urls
        else:
            store_last_seen_id(last_seen_id, FILE_NAME)
            loop_crawl()

def baca_json():
    #load the data into an element
    with open('output.json') as f:
            data = json.load(f)

    #dumps the json object into an element
    json_str = json.dumps(data)

    #load the json to a string
    resp = json.loads(json_str)

    #extract an element in the response
    return (resp[0]['article'])

def smz():
    text = baca_json()

    return summarize(text, ratio=0.25)

def baca_judul():
    with open('output.json') as f:
            data = json.load(f)

    json_str = json.dumps(data)

    resp = json.loads(json_str)

    return (resp[0]['headline'])

def tweetit(filename):
    last_seen_id = retrieve_last_seen_id(FILE_NAME)
    mentions = api.mentions_timeline(last_seen_id, tweet_mode='extended')

    for mention in reversed(mentions):
        last_seen_id = mention.id
        store_last_seen_id(last_seen_id, FILE_NAME)
        text = "@" + mention.user.screen_name
        api.update_with_media(status=text, filename=filename, in_reply_to_status_id=mention.id)
        print('%s was tweeted' % filename)

def sum_in_pic():
    download = Image.open('download.jpeg')
    enhancer = ImageEnhance.Brightness(download)
    enhancer.enhance(0.5).save('bg.jpeg')
    text = smz()
    judul = baca_judul()
    judul = textwrap.fill(judul, width=25)
    text = textwrap.fill(text, width=60)
                            
    image = Image.open('bg.jpeg')
    draw = ImageDraw.Draw(image)
    (x, y) = (40, 220)
    color = 'rgb(255, 255, 255)'
    font = ImageFont.truetype('tmsgeo.ttf', size=15)
    font_judul = ImageFont.truetype('NEXT_ART.otf', size=24)
    draw.text((50, 100), text=judul, fill=color, font=font_judul)
    draw.text((x, y), text=text, fill=color, font=font)

    image.save('save_this.jpeg')
    tweetit('save_this.jpeg')

def run():
    sum_in_pic()
    print("finish")

class ArticleSpider(scrapy.Spider):
    name = "article"
    
    def start_requests(self):
        link = take_link()
        start_urls = link
        start_urls = urlopen(start_urls[0]).geturl()
        start_urls = [start_urls]

        for url in start_urls:
            yield scrapy.Request(url)

    def parse(self, response):
        judul = response.xpath(".//div[@class='jdl']//h1/descendant::text()").extract()
        in_content = response.xpath(".//div[@id='detikdetailtext']/descendant::text()").extract()
        link = response.xpath("//div[@id='detikdetailtext']//table[@class='linksisip']/descendant::text()").extract()
        google_tag = response.xpath("//div[@id='detikdetailtext']//script/descendant::text()").extract() 
        tag = response.xpath("//div[@id='detikdetailtext']//div[@class='detail_tag']/descendant::text()").extract() 
        not_content = link + google_tag + tag
        #content = list(set(in_content).difference(not_content))
        content = [elem for elem in in_content if elem not in not_content ]
        data = [{"headline" : " ".join(judul), "article" : " ".join(content)}]

        with open('output.json', 'w') as outfile:
            json.dump(data, outfile, indent = 4, sort_keys=True)
            outfile.write('\n')
        run()
        print("finish")

def sleep(_, duration=5):
    print(f'sleeping for: {duration}')
    time.sleep(duration)  # block here

def crawl(runner):
    d = runner.crawl(ArticleSpider)
    d.addBoth(sleep)
    d.addBoth(lambda _: crawl(runner))
    return d

def loop_crawl():
    runner = CrawlerRunner(get_project_settings())
    crawl(runner)
    reactor.run()

if __name__ == "__main__":
    loop_crawl()