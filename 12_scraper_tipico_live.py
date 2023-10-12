from helpers import TipicoHelper

# Tennis
url = 'https://sports.tipico.de/en/live/tennis'
dict_markets =  {
       'match-winner'          : 'Match Winner',
       'set-winner'            : 'Set Winner',
       'tie-break-yes-no'      : 'Tie-Break in Set',                    
       }
# Soccer
# url = 'https://sports.tipico.de/en/live/soccer'
# dict_markets =  {
#         '3-way'                 : '3-Way',
#         'next-goal'             : 'Next goal',    # TODO: Consider Handicap!!!
#         'btts'                  : 'Both Teams to Score'                 
#         }
interval = 5

# Main
hlp = TipicoHelper(url, dict_markets)
hlp.acceptCookies()
hlp.findEventsTable(live=True)
hlp.setDropdowns()
hlp.fetchLiveEvents()
event_filter, market_filter = hlp.requestLiveFilters()
hlp.fetchLivePeriodic(event_filter, market_filter, interval)
