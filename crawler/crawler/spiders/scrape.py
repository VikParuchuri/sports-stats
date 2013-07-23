from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.selector import HtmlXPathSelector
from scrapy.item import Item, Field
import re

bbr_base_url = ""

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

class SimpsonsSpider(CrawlSpider):
    name = "snpp"
    allowed_domains = ['www.snpp.com', 'snpp.com']
    start_urls = [bbr_base_url]
    rules = [Rule(SgmlLinkExtractor(allow=['/episodes/\w+.html']), 'parse_script')]

    def fix_field_names(self, field_name):
        field_name = re.sub(" ","_", field_name)
        field_name = re.sub(":","", field_name)
        return field_name

    def parse_script(self, response):
        x = HtmlXPathSelector(response)
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
        pop_head = play_by_play.select('thead/tr/th/text()').extract()
        pop_head = [z for z in pop_head if z not in ["R/O"]]
        pop_descs = play_by_play.select('tbody/tr[@class="partial_table black_text bold_text shade_text"]/td/span/text()').extract()
        pop = []
        for i in xrange(0,len(pop_descs)):
            pop_rows = play_by_play.select('tbody/tr[@id="event_{0}"]/td/text()'.format(i+1)).extract()
            if len(pop_rows)==10:
                pop_rows = pop_rows[0:5] + [0] + pop_rows[4:]
            pop_dict = {pop_head[z]:pop_rows[z] for z in xrange(0,len(pop_head))}
            pop_dict.update({'event' : i})
            pop.append(pop_dict)
        lineup_positions = lineups.select('tbody/tr/td/text()').extract()
        lineup_names = lineups.select('tbody/tr/td/a/text()').extract()
        away_lineup = []
        home_lineup = []
        for i in xrange(0,len(lineup_names)):
            player = lineup_names[i]
            position = lineup_positions[i*2]
            order = lineup_positions[(i*2-1)]
            ld = {'player' : player, 'position' : position, 'order' : order}
            if i%2 == 0:
                away_lineup.append(ld)
            else:
                home_lineup.append(ld)
        games = []
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
                    headers = t.select('thead/tr/th/text()').extract()
                    stat_type = headers[0].lower()
                    headers[0] = "position"
                    headers = [h.lower() for h in headers]
                    players = t.select('tbody/tr[@class="normal_text"]')
                    for p in players:
                        tds = p.select('td/text()').extract()
                        try:
                            name = p.select('td/a/text()')[0].extract()
                        except Exception:
                            name = None
                        datarow = {headers[i] : tds[i] for i in xrange(0,len(tds))}
                        datarow.update({'type' : stat_type, 'player' : name})
                        if datarow and datarow['player']:
                            data.append(datarow)
            game['data'] = data
            games.append(game)
        return games