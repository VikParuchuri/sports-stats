from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.selector import HtmlXPathSelector
from scrapy.item import Item, Field
import re

import logging
log = logging.getLogger(__name__)

bbr_base_url = "http://www.baseball-reference.com/boxes/"

good_years = range(1995,2013)

year_links = ['/boxes/{0}.shtml'.format(i) for i in good_years]

class Game(Item):
    url = Field()
    away_team = Field()
    home_team = Field()
    date = Field()
    data = Field()
    location = Field()
    umpires = Field()
    game_length = Field()
    weather = Field()
    fieldcond = Field()
    team = Field()
    home_lineup = Field()
    away_lineup = Field()
    play_by_play = Field()

class BBRSpider(CrawlSpider):
    name = "bbr"
    allowed_domains = ['www.baseball-reference.com', 'baseball-reference.com']
    start_urls = [bbr_base_url]
    rules = [
        Rule(SgmlLinkExtractor(allow=year_links)),
        Rule(SgmlLinkExtractor(allow=('/play-index/st.cgi?date=.+'))),
        Rule(SgmlLinkExtractor(allow=['/boxes/.+/.+.shtml']), 'parse_game')
    ]

    def fix_field_names(self, field_name):
        field_name = re.sub(" ","_", field_name)
        field_name = re.sub(":","", field_name)
        return field_name

    def parse_game(self, response):
        x = HtmlXPathSelector(response)
        games = []
        try:
            away, home = x.select('//span[@class="xx_large_text bold_text"]/text()').extract()
            teams = [away,home]
            date, location = x.select('//div[@class="bold_text float_left"]/text()').extract()
            tables = x.select('//table[@class="sortable  stats_table"]')[0:4]
            umpires = x.select('//div[@id="Umpires"]/text()').extract()[0]
            game_length = x.select('//div[@id="gametime"]/text()').extract()[0]
            weather = x.select('//div[@id="weather"]/text()').extract()[0]
            fieldcond = x.select('//div[@id="fieldcond"]/text()').extract()[0]
            lineups = x.select('//table[@class="sortable  stats_table"]')[4]
            play_by_play = x.select('//table[@id="play_by_play"]')[0]
            pop_head = get_row(play_by_play.select('thead/tr/th'))
            pop_descs = get_row(play_by_play.select('tbody/tr[@class="partial_table black_text bold_text shade_text"]/td/span'))
            pop = []
            try:
                for i in xrange(0,len(pop_descs)):
                    pop_rows = get_row(play_by_play.select('tbody/tr[@id="event_{0}"]/td'.format(i+1)))
                    #rob,pit = play_by_play.select('tbody/tr[@id="event_{0}"]/td/span/text()'.format(i+1))[0:2].extract()
                    pop_dict = {pop_head[z].lower():pop_rows[z] for z in xrange(0,len(pop_head))}
                    pop_dict.update({'event' : i,})
                    pop.append(pop_dict)
            except Exception:
                log.exception("Problem parsing play by play.")
            lineup_positions = [p for p in get_row(lineups.select('tbody/tr/td')) if p!=""]
            away_lineup = []
            home_lineup = []
            counter=0
            for i in xrange(0,len(lineup_positions),3):
                if len(lineup_positions)>i+2:
                    order,player,position = lineup_positions[i:i+3]
                    ld = {'player' : player, 'position' : position, 'order' : order}
                    if counter%2 == 0:
                        away_lineup.append(ld)
                    else:
                        home_lineup.append(ld)
                    counter+=1
            for (i,te) in enumerate(teams):
                game = Game()
                game['date'] = date
                #game['url'] = response.url
                game['location'] = location
                game['umpires'] = umpires
                game['game_length'] = game_length
                game['weather'] = weather
                game['fieldcond'] = fieldcond
                game['data'] = []
                game['home_team'] = home
                game['away_team'] = away
                game['team'] = te
                game['home_lineup'] = home_lineup
                game['away_lineup'] = away_lineup
                game['play_by_play'] = pop
                data = []
                for t in tables:
                    tid = t.select('@id').extract()[0]
                    if te in tid:
                        headers = get_row(t.select('thead/tr/th'))
                        stat_type = headers[0].lower()
                        headers[0] = "player"
                        headers = [h.lower() for h in headers]
                        players = t.select('tbody/tr[@class="normal_text"]')
                        for p in players:
                            if stat_type=="batting":
                                headers = headers + ["altpos"]
                            tds = get_row(p.select('td'))
                            try:
                                bat = p.select('td/text()')[0].extract()
                            except Exception:
                                bat = None
                                log.exception("Problem parsing player name.")
                            datarow = {headers[i] : tds[i] for i in xrange(0,len(tds))}
                            datarow.update({'type' : stat_type, 'bat' : bat})
                            if datarow and datarow['player']:
                                data.append(datarow)
                game['data'] = data
                games.append(game)
        except Exception:
            log.exception("Could not parse game.")
        return games

def get_row(sels):
    ftext= []
    for s in sels:
        s = s.extract()
        ftext.append(get_text(s))
    return ftext

def get_text(text):
    text = extract_text(text)
    text = re.sub("<.+>","",text)
    return text

def extract_text(text):
    m = re.search('>(.+)<',text)
    if m is None:
        return text
    else:
        text = m.group(1)
    return get_text(text)