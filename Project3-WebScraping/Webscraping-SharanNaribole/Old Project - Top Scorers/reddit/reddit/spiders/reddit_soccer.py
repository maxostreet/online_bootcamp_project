import scrapy
import datetime as dt
import pandas as pd
import re
import unicodedata
from  reddit.items import RedditItem
import time

#The goal is to collect posts from r/soccer for last 150 days ago with words
#(scores or goal) and (vs or against) in them


class RSoccerSpider(scrapy.Spider):
    name = "rsoccer"

    allowed_domains = ["reddit.com"]
    start_urls = ['https://www.reddit.com/r/soccer/']
    counter = 0
    Nexclude_pages = 5
    Nsubmission_interval = 100 #days
    current_time = dt.datetime.now()
    terminate = False #terminate when submission creation exceeds Nsubmission_interval

    def parse(self,response):
        self.logger.info("Visited %s",response.url)
        self.counter += 1

        if(self.terminate == True):
            return 0

        #Excluding recent posts in Nexclude_pages whose score might be still change in the near future
        if(self.counter > self.Nexclude_pages):
            #Extracting the titles
            #Only posts with external links as the goals are usually shared through external links to streamable, mixtape.moe, gyfcat etc.
            titles = response.css('.outbound::text').extract()
            links = response.css('.outbound::attr(href)').extract()
            timestamps = response.css('.live-timestamp::attr(title)').extract()
            comments = response.css('.comments::text').extract()
            scores = response.css('.score.likes::text').extract()

            #Going through the submissions
            for i in range(len(titles)):

                #Check if the keywords for goal submissions are present in current submission
                if(self.check_goal(self.decompose(titles[i])) != True):
                    continue

                #Check if submission data exceeds the time difference upper limit
                #if self.exceed_time_diff(pd.to_datetime(timestamps[i])) == True:
                #    self.terminate = True
                #    raise CloseSpider('Submission History Exceeded Limit')

                #Item Creation
                item = RedditItem()
                item['title'] = self.decompose(titles[i])
                item['comments'] = comments[i]
                item['score'] = scores[i]
                item['link'] = links[i]
                item['time'] = timestamps[i]
                print(timestamps[i], " \n")

                yield(item)

        #Pauses for 10 seconds
        #time.sleep(10)

        if(self.terminate == False):
            next_page = response.css('.next-button a::attr(href)').extract_first()

            if next_page is not None:
                yield scrapy.Request(response.urljoin(next_page), callback = self.parse)

    #Compress special characters to English components
    def decompose(self,x):
        x = unicodedata.normalize('NFD',x).encode('ascii','ignore')
        return x.decode("utf-8")

    #Matching a word in a sentence
    def word_locate(self,x,y):
        #x = keyword, y = sentence
        match = re.search(r'\b({0})\b'.format(x), y)
        res = False
        if match:
            res = True
        return res

    #Testing presence of keywords in reddit submission title
    def check_goal(self,title):
        check = False
        keywords =['goal','scores','vs','against']
        keywords_bool =list(map(lambda keyword:self.word_locate(keyword,title),keywords))

        if(((keywords_bool[0]==True) or (keywords_bool[1]==True)) and ((keywords_bool[2]==True) or (keywords_bool[3]==True))):
            check = True

        return check

    # Checking if time difference between current time and the submission creation exceeds defined upper bound
    def exceed_time_diff(self,submission_time):
        delta = pd.to_timedelta(self.current_time - submission_time)
        match = re.search('\d+',str(delta))

        print("Days Delta =", int(match.group())," \n")

        res = False
        #Check if time difference in days exceeds the upper limit
        if(int(match.group()) > self.Nsubmission_interval):
            res = True

        return res
